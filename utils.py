# -*- coding: utf-8 -*-
"""
Utils for ageobot.

"""
import datetime

import boto3


def get_url(databytes, uuid1):
    print('entering get_url()')

    file_link = ''
    now = datetime.datetime.now()
    expires = now + datetime.timedelta(minutes=240)
    success = False

    try:
        from secrets import KEY, SECRET
        session = boto3.session.Session(aws_access_key_id=KEY,
                                        aws_secret_access_key=SECRET,
                                        region_name='us-east-1'
                                        )
        client = session.client('s3')
        key = uuid1 + '.segy'
        bucket = 'ageobot'
        acl = 'public-read'  # For public file.
        params = {'Body': databytes,
                  'Expires': expires,
                  'Bucket': bucket,
                  'Key': key,
                  'ACL': acl,
                  }
        r = client.put_object(**params)
        success = r['ResponseMetadata']['HTTPStatusCode'] == 200
    except:
        print('Upload to S3 failed')

    print(str(success))

    if success:
        # Only do this if successfully uploaded, because
        # you always get a link, even if no file.
        if acl == 'public-read':
            file_link = 'https://s3.amazonaws.com/{}/{}'.format(bucket, key)
        else:
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
