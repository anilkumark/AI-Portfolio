#importing required libraries
import torch
from torch import nn
from collections import OrderedDict
import torch.utils.data as Data
from torch import Tensor
import numpy as np
import torch
from torch.autograd import Variable


class Pytorch_NN:

    def __init__(self, X, X_train, y_train, X_test, y_test):
        """

        :param X:
        :param X_train:
        :param y_train:
        :param X_test:
        :param y_test:
        """
        # ## Sequential Neural Network
        # Hyperparameters for our network
        input_size = X.shape[1]
        hidden_sizes = [128, 64]
        output_size = 2 #number of target column class

        model = self.get_model_t1(hidden_sizes, input_size, output_size)
        print(model)

        self.get_model_t2(hidden_sizes, input_size, output_size)
        self.train(model, X_train, y_train, X_test, y_test)


    def train(self, model, X_train, y_train, X_test, y_test):
        """
        Training and Evaluating the model
        :param model:
        :param X_train:
        :param y_train:
        :param X_test:
        :param y_test:
        :return:
        """
        # Define the loss
        criterion = nn.NLLLoss()
        from torch import optim
        # Optimizers require the parameters to optimize and a learning rate
        optimizer = optim.SGD(model.parameters(), lr=0.01)
        X_train = Tensor(X_train)
        y_train = Tensor(np.array(y_train))
        BATCH_SIZE = 64
        # EPOCH = 200
        torch_dataset = Data.TensorDataset(X_train, y_train)
        loader = Data.DataLoader(
            dataset=torch_dataset,
            batch_size=BATCH_SIZE,
            shuffle=True, num_workers=0, )
        # ## Training the model
        epochs = 100
        for e in range(epochs):
            running_loss = 0
            for step, (batch_x, batch_y) in enumerate(loader):

                b_x = Variable(batch_x)
                b_y = Variable(batch_y.type(torch.LongTensor))

                # Training pass
                optimizer.zero_grad()

                output = model(b_x)
                loss = criterion(output, b_y)
                loss.backward()
                optimizer.step()

                running_loss += loss.item()

            else:
                print(f"Training loss: {running_loss / len(X_train)}")
        X_test = Tensor(X_test)
        y_test = Tensor(np.array(y_test))
        z = model(X_test)
        yhat = list(z.argmax(1))
        y_test = list(y_test)
        from sklearn.metrics import accuracy_score
        print( f'Accuracy of model is : {round(100*accuracy_score(y_test, yhat),2)}%')

    def get_model_t2(self, hidden_sizes, input_size, output_size):
        """
        Model Type 2
        :param hidden_sizes:
        :param input_size:
        :param output_size:
        :return:
        """
        model_dict = nn.Sequential(OrderedDict([
            ('fc1', nn.Linear(input_size, hidden_sizes[0])),
            ('relu1', nn.ReLU()),
            ('fc2', nn.Linear(hidden_sizes[0], hidden_sizes[1])),
            ('relu2', nn.ReLU()),
            ('output', nn.Linear(hidden_sizes[1], output_size)),
            ('softmax', nn.Softmax(dim=1))]))

        return model_dict

    def get_model_t1(self, hidden_sizes, input_size, output_size):
        """
        Model Type 1
        :param hidden_sizes:
        :param input_size:
        :param output_size:
        :return:
        """
        # Build a feed-forward network
        model = nn.Sequential(nn.Linear(input_size, hidden_sizes[0]),
                              nn.ReLU(),
                              nn.Linear(hidden_sizes[0], hidden_sizes[1]),
                              nn.ReLU(),
                              nn.Linear(hidden_sizes[1], output_size),
                              nn.Softmax(dim=1))
        return model

