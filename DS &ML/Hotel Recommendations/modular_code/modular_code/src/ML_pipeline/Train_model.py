import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from xgboost import XGBClassifier
from sklearn.tree import DecisionTreeClassifier
import math
import joblib


def train_model(x_train, x_test, y_train, y_test, model_name, path_to_save):
    model_dict = {
        'logistic_reg': LogisticRegression,
        'gaussian_nb': GaussianNB,
        'RF_cls': RandomForestClassifier,
        'dtree_cls': DecisionTreeClassifier,
        'xgb_cls': XGBClassifier,
        'knn_cls': KNeighborsClassifier
    }
    if model_name not in list(model_dict.keys()):
        raise ValueError(
            f"Only these options for model_name are allowed : {list(model_dict.keys())}")
    model = model_dict[model_name]()
    model.fit(x_train, y_train)
    test_pred = model.predict(x_test)
    train_pred = model.predict(x_train)
    # Save the model as a pickle in a file
    # filename = 'output/'+ str(model_name) + '.pkl'
    joblib.dump(model, path_to_save)
    print('Model saved as pkl file in '+str(path_to_save))
    return train_pred, test_pred
