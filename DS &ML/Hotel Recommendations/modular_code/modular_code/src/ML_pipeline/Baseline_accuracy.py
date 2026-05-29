from sklearn.metrics import accuracy_score
import pandas as pd
import numpy as np


def baseline_accuracy(Y_test, most_occured_y):
    test_rows = Y_test.shape[0]
    predicted_values = np.ones(test_rows) * most_occured_y
    acc = accuracy_score(Y_test, predicted_values)
    return acc
