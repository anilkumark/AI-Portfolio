LightSail Deployment

AWS CLI Installation link :
https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html

LIGHTSAIL CLI Installation Link:
https://lightsail.aws.amazon.com/ls/docs/en_us/articles/amazon-lightsail-install-software

DOCKER Installation Link:
https://www.digitalocean.com/community/tutorials/how-to-install-and-use-docker-on-ubuntu-18-04


Note: If you want to copy the entire code folder to the EC2 Instance, then execute this command:

scp -i "<location of pem file in your local system>" -r "<location-of-code-folder>" ubuntu@<ec2-ip>compute-1.amazonaws.com:/home/ubuntu/


Install Docker > AWS CLI > LIGHTCTL. Follow the order of installation and start the deployment

Step 1: 
Create a docker file with 5000 port exposed

Step 2:
```sudo docker build -t flask-container .```

Step 3: 
```sudo docker run -p 5000:5000 flask-container```
* check if the container is running or not

Step 4:
```sudo aws lightsail create-container-service --service-name flask-service --power small --scale 1```
The output of the above command has the following
"state": "PENDING",
when the state becomes "Active" perform next step


Important:
````Create a new IAM Role and attach these policies to that role. Once the role is configured with all the policies, attach that role to the EC2 Instance```

Add these policies to the role:

1. AmazonEC2ContainerRegistryPowerUser
2. AmazonS3FullAccess
3. Create an inline policy

{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "lightsail:*",
            "Resource": "*"
        }
    ]
}


Step 5:
```aws lightsail push-container-image --service-name flask-service --label flask-container --image flask-container```


Note: 

````If you face push error: "platform" requires API version 1.46, but the Docker daemon API version is 1.43``
Then execute this command:
1. sudo apt-get update
2. sudo apt-get install ca-certificates curl gnupg
3. sudo install -m 0755 -d /etc/apt/keyrings
4. curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
5. echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
6. sudo apt-get update
7. sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin



At the ouput of this command there will the following line 
Refer to this image as ":flask-service.flask-container.X" in deployments.

in which X will be number from 1 to 10, take that number and attach it in the containers json.

Step 6:
Create a new file, containers.json. 

{
    "flask": {
        "image": ":flask-service.flask-container.X",  # replace this X from Step 5 Out
        "ports": {
            "5000": "HTTP"
        }
    }
}

Step 7:
Create a new file, public-endpoint.json. 
{
    "containerName": "flask",
    "containerPort": 5000
}

Step 8:
```aws lightsail create-container-service-deployment --service-name flask-service --containers file://containers.json --public-endpoint file://public-endpoint.json```


After some time run the following command
```aws lightsail get-container-services --service-name flask-service```

in the ouput if the state is running then the model is deployed
```"state": "RUNNING"```,

Step 9:
Cleanup
```aws lightsail delete-container-service --service-name flask-service```

Putty Installation Link
* https://www.putty.org/

Step 10:
TEST deployed Application through POST Request

1. On the EC2 instance, navigate to the Input folder inside the code directory that you copied to the EC2 instance.

2. Make POST Request by executing this command

```curl -X POST -F "data=@CallCenterData.csv" <lightsail-container-instance-url>```