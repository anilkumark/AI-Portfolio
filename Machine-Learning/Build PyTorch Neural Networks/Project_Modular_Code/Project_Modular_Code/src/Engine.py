import pandas as pd
from MLPipeline.Pytorch_NN import Pytorch_NN
from MLPipeline.Preprocessing import Preprocessing

# Reading the data
df = pd.read_csv("../Input/data.csv")

#put name of columns you want to drop
data = Preprocessing(df).drop(["customer_id", "phone_no", "year"])

#dropping null values
data =Preprocessing(data).dropna()

#scaling numerical features
data=Preprocessing(data).scale()

#label encoding categorical features
data=Preprocessing(data).encode()




# splitting data into train and test
target_col='churn' #Put target column name here
X, X_train, X_test, y_train, y_test = Preprocessing(data).split_data(target_col)

# # Training the network
Pytorch_NN(X, X_train, y_train, X_test, y_test)
