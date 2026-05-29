import pandas as pd
import numpy as np


def convert_into_datetime(df, col):
    df[col] = pd.to_datetime(
        df[col], infer_datetime_format=True, errors='coerce')
    return df


def date_difference(df, col1, col2, new_col_name='Duration'):
    if new_col_name in df:
        raise KeyError(
            f"{new_col_name} column already exists. Please enter a different value for new_col_name")
    df[new_col_name] = (df[col1] - df[col2]).astype('timedelta64[D]')
    return df


def year_from_date(df, date_col, new_col_name='year'):
    if new_col_name in df:
        raise KeyError(
            f"{new_col_name} column already exists. Please enter a different value for new_col_name")
    df[new_col_name] = pd.DatetimeIndex(df[date_col]).year
    return df


def month_from_date(df, date_col, new_col_name='month'):
    if new_col_name in df:
        raise KeyError(
            f"{new_col_name} column already exists. Please enter a different value for new_col_name")
    df[new_col_name] = pd.DatetimeIndex(df[date_col]).month
    return df


def day_from_date(df, date_col, new_col_name='day'):
    if new_col_name in df:
        raise KeyError(
            f"{new_col_name} column already exists. Please enter a different value for new_col_name")
    df[new_col_name] = pd.DatetimeIndex(df[date_col]).day
    return df
