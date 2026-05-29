import pandas as pd
import numpy as np
import joblib


def solutionising(X, Y, k, model_path):
    model = joblib.load(model_path)
    prob_predictions = model.predict_proba(X)
    y_index_reset = Y.reset_index(drop=True)
    temp = np.flip(prob_predictions.argsort(axis=1), axis=1)[:, 0:k]
    predicted_in_top_k = 0
    for i in range(len(y_index_reset)-1):
        if y_index_reset[i] in temp[i, :]:
            predicted_in_top_k = predicted_in_top_k + 1
    accuracy = predicted_in_top_k/len(y_index_reset) * 100
    return accuracy
