import json
import boto3
import os
import base64
import urllib.parse
import re

isLambda   = "LAMBDA_RUNTIME_DIR" in os.environ

####################################################################################
######### simple Queue abstraction layer between the logic and the implementation  #
####################################################################################
class Queue():
    def __init__(self, **kwargs):
        self.region = kwargs.get('region','us-east-1')
        self.queue_url = kwargs.get('queue_url')
        self.authorization_structure = dict(
            region_name=self.region,
            profile_name = None if isLambda else 'metamoneta'
        )
        self.session = boto3.session.Session(**self.authorization_structure)
        self.queue = self.session.client('sqs')

    def enQueue(self, payload, **kwargs):
        if type(payload) in [dict, list]:
            payload = json.dumps(payload)
        self.response = self.queue.send_message(QueueUrl=self.queue_url, MessageBody=payload)
        return self.response

    def deQueue(self, **kwargs):
        number_of_messages_to_read = kwargs.get('number_of_messages_to_read',10)
        delete_read_messages = bool(kwargs.get('delete_read_messages',True))
        return_full_sqs_message = bool(kwargs.get('return_full_sqs_message',False))
        self.response = self.queue.receive_message(
           QueueUrl=self.queue_url,
           MaxNumberOfMessages=number_of_messages_to_read
        )
        messages = self.response.get('Messages', [])
        return_values = []
        for message in messages:
            # Delete the message from the queue
            if delete_read_messages:
                self.queue.delete_message(
                    QueueUrl=self.queue_url,
                    ReceiptHandle=message['ReceiptHandle']
                )
            if return_full_sqs_message:
                return_values.append(message)
            else:
                return_values.append(json.loads(message['Body']))
            # 10 is the maximum number of returned messages in SQS,
            # so we clear the queue to be on the safe side
            if delete_read_messages and len(messages)>=10:
                self.purgeQueue()
        return return_values

    def getQueueDepth(self,  **kwargs):
        self.response = self.queue.get_queue_attributes(QueueUrl=self.queue_url,
                                                        AttributeNames = ['ApproximateNumberOfMessages']
                                                        )
        return self.response['Attributes']['ApproximateNumberOfMessages']

    def purgeQueue(self):
        try:
            self.response = self.queue.purge_queue(QueueUrl=self.queue_url)
        except self.queue.exceptions.PurgeQueueInProgress as e:
            self.response = {"error": str(e)}
# ------ end of class

# Check is event is authorized
def authorized(event):
    apikey = os.environ.get('APIKEY')
    authorization_object = event['headers'].get('authorization', 'no').split()
    authorization_qs = event.get('queryStringParameters', {}).get('key', '')
    if (len(authorization_object) == 2 and authorization_object[1] == apikey) or authorization_qs == apikey:
        return True
    else:
        return False

# Event bodies arrive on POST or PUT http events.
# This helper function deals with all kinds of
# content and different encodings.
def get_body(event):
    isBase64Encoded = event.get("isBase64Encoded", False)
    event_body_raw = event.get('body', '{}')
    body_content_type = event['headers'].get("content-type", "text/plain")
    event_body = base64.b64decode(event_body_raw) if isBase64Encoded else event_body_raw
    json_pattern = '^application\/(vnd\.api\+)?json.*$'
    is_JSON = re.match(json_pattern, body_content_type)
    if body_content_type == "application/x-www-form-urlencoded":
        response = urllib.parse.parse_qs(event_body)
        if not response:
            try:
                response = json.loads(event_body)
            except:
                response = {}
    elif is_JSON:
        response = json.loads(event_body)
    else:
        response = dict(body=event_body)
    return response

# Return the response for /diagnostics, if enabled
def diagnostics(event, context):
    response = dict(event)
    response["environ"] = dict(os.environ)
    return response

####################################################################
def main(event=None, context=None):
    print(json.dumps(event))
    skip_authorization = os.environ.get('SKIP_AUTHORIZATION','false').lower()=='true'

    if not (authorized(event)) and not skip_authorization:
        return {
            'statusCode': 401,
            'body': 'unauthorized'
        }
    path = event['rawPath'].lower()
    allow_diagnostics = os.environ.get('ALLOW_DIAGNOSTICS','false').lower()=='true'
    if allow_diagnostics and path == "/diagnostics":
        response = diagnostics(event, context)
        return {
            'statusCode': 200,
            'body': json.dumps(response)
        }
    event_message = get_body(event)
    method = event['requestContext']['http']['method'].lower()

    challenge = event_message.get('challenge')
    if challenge and method == 'post':
        response = event_message
        return {
            'statusCode': 200,
            'body': json.dumps(response)
        }

    sqs = Queue(
        region=os.environ.get('AWS_REGION','us-east-1'),
        queue_url=os.environ['QUEUE_URL']
    )

    return_full_sqs_message = os.environ.get('RETURN_FULL_SQS_MESSAGE','false')=='true'
    return_only_message_count = os.environ.get('RETURN_ONLY_MESSAGE_COUNT','true')=='true'

    if path == "/read" and method == 'get':
        if return_only_message_count:
            response = sqs.getQueueDepth()
            if int(response) > 0:
                sqs.purgeQueue()
        else:
            messages = sqs.deQueue(
                return_full_sqs_message=return_full_sqs_message
            )
            response = json.dumps(messages, indent=4)
        return {
            'statusCode': 200,
            'body': response
        }

    elif path == "/write" and method == 'post':
        sqs.enQueue(event_message)
        return {
            'statusCode': 200,
            'body': "ok"
        }

    else:
        return {
            'statusCode': 404,
            'body': "not found"
        }
