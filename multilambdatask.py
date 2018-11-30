import asyncio

from lambdatask import LambdaTask

class MultiLambdaTask(LambdaTask):
    async def __call__(self, **app_data):
        futures = [
            super(MultiLambdaTask, self).__call__(**lambda_data) for
            lambda_data in self.create_lambda_data_arr(**app_data)
        ]
        return await asyncio.gather(*futures)

    def create_lambda_data_arr(self, **app_data):
        return [
            {'method': method, 'args_dict': args_dict} for
            method, args_dict in zip(app_data['methods'], app_data['args_dicts'])
        ]