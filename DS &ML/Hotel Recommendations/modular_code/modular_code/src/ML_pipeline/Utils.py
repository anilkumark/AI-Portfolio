import pandas as pd


def read_dataset(path, nrows=100000):
    df = pd.read_csv(path, nrows=nrows)
    return df
