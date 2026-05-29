

from sklearn.preprocessing import LabelEncoder

from sklearn.preprocessing import MinMaxScaler

class Preprocessing:

    def __init__(self, data):
        self.data=data

    #columns to drop
    def drop(self,cols):
        col=list(cols)
        self.data.drop(col,axis=1,inplace=True)
        return self.data
    
    #dropping null values
    def dropna(self):
        self.data.dropna(axis=0,inplace=True)
        return self.data 
    
    #scaling features
    def scale(self):
        num_cols=self.data.select_dtypes(exclude=['object']).columns.tolist() #getting numeircal columns 
        scale=MinMaxScaler()
        self.data[num_cols]=scale.fit_transform(self.data[num_cols])
        return self.data
    
    #label encoding
    def encode(self):
        cat_cols=self.data.select_dtypes(include=['object']).columns.tolist() #getting categorical columns
        le=LabelEncoder()
        self.data[cat_cols]=self.data[cat_cols].apply(le.fit_transform)
        return self.data


    #splitting data. 
    def split_data(self,target_col):
        X = self.data.drop(target_col, axis=1)
        Y = self.data[target_col].astype(int)
        # split a dataset into train and test sets
        from sklearn.model_selection import train_test_split
        X_train, X_test, y_train, y_test = train_test_split(X.values, Y, test_size=0.2, random_state=42)
        return X, X_train, X_test, y_train, y_test
