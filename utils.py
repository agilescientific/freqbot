# -*- coding: utf-8 -*-
"""
Utils for ageobot.

"""
import datetime

import boto3


def get_url(databytes, uuid1):
    file_link = ''
    now = datetime.datetime.now()
    expires = now + datetime.timedelta(minutes=61)

    try:
        from secrets import KEY, SECRET
        print('creating session')
        session = boto3.session.Session(aws_access_key_id=KEY,
                                        aws_secret_access_key=SECRET,
                                        region_name='us-east-1'
                                        )
        client = session.client('s3')

        key = uuid1 + '.segy'
        bucket = 'elasticbeanstalk-us-east-1-991793580031/ageobot/segy'
        params = {'Body': databytes,
                  'Expires': expires,
                  'Bucket': bucket,
                  'Key': key}
        r = client.put_object(**params)
        assert r['ResponseMetadata']['HTTPStatusCode'] == 200
    except:
        print('Upload to S3 failed')

    try:
        params = {'Bucket': bucket,
                  'Key': key}
        file_link = client.generate_presigned_url('get_object',
                                                  Params=params,
                                                  ExpiresIn=3600)
    except:
        print('Retrieval of S3 link failed')

    return file_link


def build_params(method, avg, t_min, t_max, region, tr_sp, traces='', url=''):
    params = {'method': method}
    params['avg'] = avg
    params['time_range'] = [t_min, t_max]
    params['region'] = region
    params['trace_spacing'] = tr_sp
    if traces is not '':
        params['traces'] = traces.tolist()
    else:
        params['traces'] = ''
    params['url'] = url
    return params
