class Status:
    def __init__(self):
        self.status = {
            'server': {'is_active': False, 'message': ''},
            'client': {'is_active': False, 'message': ''},
            'micro': {'is_active': False, 'message': ''},
            'running':{'is_active': False, 'message': ''},
        }

    def __call__(self, field, is_active, message=''):
        if field not in self.status:
            self.status[field] = {'is_active': is_active, 'message': message}
        else:
            self.status[field]['is_active'] = is_active
            self.status[field]['message'] = message
        
    def __getattr__(self, field):
        if field in self.status:
            return lambda: self.status[field]['is_active']
        raise AttributeError(f"'Status' object has no attribute '{field}'")
    
    def message(self, field):
        if field in self.status:
            return self.status[field]['message']
