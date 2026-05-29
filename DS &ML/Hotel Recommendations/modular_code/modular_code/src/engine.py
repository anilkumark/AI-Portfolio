import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from ML_pipeline.Utils import read_dataset
from ML_pipeline.Impute import impute
from ML_pipeline.Date_time_conversion import convert_into_datetime
from ML_pipeline.Date_time_conversion import date_difference
from ML_pipeline.Date_time_conversion import year_from_date
from ML_pipeline.Date_time_conversion import month_from_date
from ML_pipeline.Date_time_conversion import day_from_date
from ML_pipeline.Baseline_accuracy import baseline_accuracy
from ML_pipeline.Train_model import train_model
from ML_pipeline.Evaluate_results import evaluate_results
from ML_pipeline.Solutionising import solutionising


# Read Dataset
train = read_dataset('../input/train.csv', nrows=200000)
test = read_dataset('../input/test.csv', nrows=100000)

# Imputation
train = impute(train, 'orig_destination_distance', method='mean')
test = impute(test, 'orig_destination_distance', method='mean')
train.dropna(inplace=True)
test.dropna(inplace=True)

# Feature Engineering
train = convert_into_datetime(train, 'date_time')
train = convert_into_datetime(train, 'srch_ci')
train = convert_into_datetime(train, 'srch_co')
train = date_difference(train, 'srch_co', 'srch_ci',
                        new_col_name='stay_duration')
train = date_difference(train, 'srch_ci', 'date_time',
                        new_col_name='no_of_prior_days_booking')
train = year_from_date(train, 'srch_ci', new_col_name='Cin_year')
train = month_from_date(train, 'srch_ci', new_col_name='Cin_ymonth')
train = day_from_date(train, 'srch_ci', new_col_name='Cin_yeday')

# Remove unwanted columns
columns = ['date_time', 'srch_ci', 'srch_co']
train.drop(columns=columns, axis=1, inplace=True)
test.drop(columns=columns, axis=1, inplace=True)

# X Y Split
Y = train['hotel_cluster']
X = train.drop(['hotel_cluster'], axis=1)
X_train, X_test, Y_train, Y_test = train_test_split(
    X, Y, test_size=0.15, random_state=1)

# Baseline accuracy
baseline_acc = baseline_accuracy(Y_test, 91)
# Train Model
train_pred, test_pred = train_model(
    X_train, X_test, Y_train, Y_test, 'logistic_reg', '../output/logistic_reg.pkl')

# Evaluate model
acc = evaluate_results(Y_test, test_pred)

# Solutionising
scc = solutionising(X_train, Y_train, 5, '../output/logistic_reg.pkl')

print("Accuracy", acc)
print("Success!!!!!!!!!")
