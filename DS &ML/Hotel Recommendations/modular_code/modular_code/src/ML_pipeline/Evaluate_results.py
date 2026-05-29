import pandas as pd
import numpy as np
from sklearn.metrics import accuracy_score
import math


def evaluate_results(actual, pred):
    acc = accuracy_score(actual, pred)
    return acc
