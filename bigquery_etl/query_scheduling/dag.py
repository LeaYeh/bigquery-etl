"""Represents an Airflow DAG."""

import attr
import cattr
from jinja2 import Environment, PackageLoader
from typing import List

from bigquery_etl.query_scheduling.task import Task
from bigquery_etl.query_scheduling import formatters
from bigquery_etl.query_scheduling.utils import (
    is_timedelta_string,
    is_date_string,
    is_email,
    is_schedule_interval,
    is_valid_dag_name,
)


AIRFLOW_DAG_TEMPLATE = "airflow_dag.j2"


class DagParseException(Exception):
    """Raised when DAG config is invalid."""

    def __init__(self, message):
        """Throw DagParseException."""
        message = f"""
        {message}

        Expected yaml format:
        name:
            schedule_interval: string,
            default_args:
                owner: string
                start_date: 'YYYY-MM-DD'
                ...
        """

        super(DagParseException, self).__init__(message)


class InvalidDag(Exception):
    """Raised when the resulting DAG is invalid."""

    pass


@attr.s(auto_attribs=True)
class DagDefaultArgs:
    """
    Representation of Airflow DAG default_args.

    Uses attrs to simplify the class definition and provide validation.
    Docs: https://www.attrs.org
    """

    owner: str = attr.ib()
    start_date: str = attr.ib()
    email: List[str] = attr.ib([])
    depends_on_past: bool = attr.ib(False)
    retry_delay: str = attr.ib("30m")
    email_on_failure: bool = attr.ib(True)
    email_on_retry: bool = attr.ib(True)
    retries: int = attr.ib(2)

    @owner.validator
    def validate_owner(self, attribute, value):
        """Check that owner is a valid email address."""
        if not is_email(value):
            raise ValueError(f"Invalid email for DAG owner: {value}.")

    @email.validator
    def validate_email(self, attribute, value):
        """Check that provided email addresses are valid."""
        if not all(map(lambda e: is_email(e), value)):
            raise ValueError(f"Invalid email in DAG email: {value}.")

    @retry_delay.validator
    def validate_retry_delay(self, attribute, value):
        """Check that retry_delay is in a valid timedelta format."""
        if not is_timedelta_string(value):
            raise ValueError(
                f"Invalid timedelta definition for {attribute}: {value}."
                "Timedeltas should be specified like: 1h, 30m, 1h15m, 1d4h45m, ..."
            )

    @start_date.validator
    def validate_start_date(self, attribute, value):
        """Check that start_date has YYYY-MM-DD format."""
        if value is not None and not is_date_string(value):
            raise ValueError(
                f"Invalid date definition for {attribute}: {value}."
                "Dates should be specified as YYYY-MM-DD."
            )

    def to_dict(self):
        """Return class as a dict."""
        return self.__dict__


@attr.s(auto_attribs=True)
class Dag:
    """
    Representation of a DAG configuration.

    Uses attrs to simplify the class definition and provide validation.
    Docs: https://www.attrs.org
    """

    name: str = attr.ib()
    schedule_interval: str = attr.ib()
    default_args: DagDefaultArgs
    tasks: List[Task] = attr.ib([])

    @name.validator
    def validate_dag_name(self, attribute, value):
        """Validate the DAG name."""
        if not is_valid_dag_name(value):
            raise ValueError(
                f"Invalid DAG name {value}. Name must start with 'bqetl_'."
            )

    @tasks.validator
    def validate_tasks(self, attribute, value):
        """Validate tasks."""
        task_names = list(map(lambda t: t.task_name, value))
        duplicate_task_names = set(
            [task_name for task_name in task_names if task_names.count(task_name) > 1]
        )

        if len(duplicate_task_names) > 0:
            raise ValueError(
                f"Duplicate task names encountered: {duplicate_task_names}."
            )

    @schedule_interval.validator
    def validate_schedule_interval(self, attribute, value):
        """
        Validate the schedule_interval format.

        Schedule intervals can be either in CRON format or one of:
        @once, @hourly, @daily, @weekly, @monthly, @yearly
        or a timedelta []d[]h[]m
        """
        if not is_schedule_interval(value):
            raise ValueError(f"Invalid schedule_interval {value}.")

    def add_tasks(self, tasks):
        """Add tasks to be scheduled as part of the DAG."""
        self.tasks = self.tasks.copy() + tasks
        self.validate_tasks(None, self.tasks)

    @classmethod
    def from_dict(cls, d):
        """
        Parse the DAG configuration from a dict and create a new Dag instance.

        Expected dict format:
        {
            "name": {
                "schedule_interval": string,
                "default_args": dict
            }
        }
        """
        if len(d.keys()) != 1:
            raise DagParseException(f"Invalid DAG configuration format in {d}")

        converter = cattr.Converter()
        try:
            name = list(d.keys())[0]
            return converter.structure({"name": name, **d[name]}, cls)
        except TypeError as e:
            raise DagParseException(f"Invalid DAG configuration format in {d}: {e}")

    def to_airflow_dag(self, client, dag_collection):
        """Convert the DAG to its Airflow representation and return the python code."""
        env = Environment(
            loader=PackageLoader("bigquery_etl", "query_scheduling/templates")
        )

        # load custom formatters into Jinja env
        for name in dir(formatters):
            func = getattr(formatters, name)
            if not callable(func):
                continue

            env.filters[name] = func

        dag_template = env.get_template(AIRFLOW_DAG_TEMPLATE)

        args = self.__dict__

        for task in args["tasks"]:
            task.with_dependencies(client, dag_collection)

        return dag_template.render(args)
