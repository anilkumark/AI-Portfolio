from sklearn.model_selection import GridSearchCV
import pandas as pd
import numpy as np
import joblib


def hyperparameter_tuning(model_path, params_grid, cv_times, x_train, x_test, y_train, y_test, save=0, path_to_save=None):
    model = joblib.load(model_path)
    CV_model = GridSearchCV(
        estimator=model, param_grid=params_grid, cv=cv_times)
    CV_model.fit(x_train, y_train)
    test_pred = CV_model.predict(x_test)
    train_pred = CV_model.predict(x_train)
    if save == 1:
        if path_to_save != None:
            joblib.dump(model, path_to_save)
            print('Model saved as pkl file in '+str(path_to_save))
        else:
            raise ValueError(f"Enter a valid path for 'path_to_save'")
    elif save == 0:
        None
    else:
        raise ValueError(f"'save' takes only 0 or 1")
    return CV_model.best_params_, train_pred, test_pred
