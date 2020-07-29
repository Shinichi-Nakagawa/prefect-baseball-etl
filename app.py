import logging
from datetime import datetime

import pandas as pd
import click
from pythonjsonlogger import jsonlogger
from prefect import task, Flow, Parameter

logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


@task
def read_csv(path: str, filename: str) -> pd.DataFrame:
    """
    Read CSV file
    :param path: dir path
    :param filename: csv filename
    :return: dataset
    :rtype: pd.DataFrame
    """
    df = pd.read_csv(f"{path}/{filename}")
    return df


@task
def calc_batting_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    打率・出塁率・長打率を計算して追加
    :param df: Batting Stats
    :return: dataset
    :rtype: pd.DataFrame
    """
    logger.debug('calc_batting_stats')
    _df = df
    _df['BA'] = round(df['H'] / df['AB'], 3)
    _df['OBP'] = round((df['H'] + df['BB'] + df['HBP']) / (df['AB'] + df['BB'] + df['HBP'] + df['SF']), 3)
    _df['TB'] = (df['H'] - df['2B'] - df['3B'] - df['HR']) + (df['2B'] * 2) + (df['3B'] * 3) + (df['HR'] * 4)
    _df['SLG'] = round(_df['TB'] / _df['AB'], 3)
    _df['OPS'] = round(_df['OBP'] + _df['SLG'], 3)
    return df


@task
def join_stats(df_player: pd.DataFrame, df_bats: pd.DataFrame) -> pd.DataFrame:
    """
    join dataframe
    :param df_player: player datea
    :param df_bats: batting stats
    :return: merged data
    :rtype: pd.DataFrame
    """
    logger.debug('join_stats')
    _df = pd.merge(df_bats, df_player, on='playerID')
    return _df


@task
def to_csv(df: pd.DataFrame, run_datetime: datetime, index=False):
    """
    export csv
    :param df: dataframe
    :param run_datetime: datetime
    :param index: include dataframe index(default: False)
    """
    logger.debug('to_csv')
    df.to_csv(f"{run_datetime.strftime('%Y%m%d')}_stats.csv", index=index)


@click.command()
@click.option("--directory", type=str, required=True, help="Baseball Dataset Path")
@click.option("--run-date", type=click.DateTime(), required=True, help="run datetime(iso format)")
def etl(directory, run_date):
    with Flow("etl") as flow:
        run_datetime = Parameter('run_datetime')
        path = Parameter('path')
        # Extract Player Data
        df_player = read_csv(path=path, filename='People.csv')
        # Extract Batting Stats
        df_batting = read_csv(path=path, filename='Batting.csv')
        # Transform Calc Batting Stats
        df_batting = calc_batting_stats(df=df_batting)
        # Transform JOIN
        df = join_stats(df_player=df_player, df_bats=df_batting)
        # Load to Data
        to_csv(df=df, run_datetime=run_datetime)

    flow.run(run_datetime=run_date, path=directory)


if __name__ == "__main__":
    etl()
