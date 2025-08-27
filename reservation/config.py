class Config:
    def __init__(self, merchant_id=None, access_token=None, sandbox=False):
        self.merchant_id = merchant_id
        self.access_token = access_token
        self.sandbox = sandbox
