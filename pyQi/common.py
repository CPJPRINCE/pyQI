"""
Qi Records modules for handling and processing records returned from Qi API calls.
This module provides classes for representing individual records and collections of records, as well as methods for converting between JSON data and Python objects.

author: Christopher Prince
license: Apache License 2.0
"""

import logging, json, base64
import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import RequestException, HTTPError, ConnectionError, Timeout
from getpass import getpass
logger = logging.getLogger(__name__)

try: 
    import keyring
except ImportError:
    keyring = None
    class KeyringError(Exception):
        pass
    logger.warning("Keyring library not found. Install with: pip install keyring to enable secure password storage. Passwords will need to be entered manually each session without keyring.")

def parse_data(d: str|dict):
    j = json.dumps(d)
    return j

def base64_encode(x: str) -> str:
    encoded = x.encode('utf-8')
    b64 = base64.b64encode(encoded)
    return "base64:" + b64.decode('utf-8').replace("=","~").replace("+","-").replace("/","_")

def _response_exception_handler(response_code: int, url: str):
    if response_code == 200:
        logger.info(f'Request successful to: {url}')
    elif response_code == 400:
        log_msg = f"400 Bad Request: The server could not understand the request due to invalid syntax. URL: {url}"
        logger.error(log_msg)
        raise ValueError(log_msg)
    elif response_code == 401:
        log_msg = f"401 Unauthorized: Authentication is required and has failed or has not yet been provided. URL: {url}"
        logger.error(log_msg)
        raise PermissionError(log_msg)
    elif response_code == 403:
        log_msg = f"403 Forbidden: You do not have permission to access this resource. URL: {url}"
        logger.error(log_msg)
        raise PermissionError(log_msg)
    elif response_code == 404:
        log_msg = f"404 Not Found: The requested resource could not be found. URL: {url}"
        logger.error(log_msg)
        raise FileNotFoundError(log_msg)
    elif response_code == 405:
        log_msg = f"405 Method Not Allowed: The request method is not supported for the requested resource. URL: {url}"
        logger.error(log_msg)
        raise ValueError(log_msg)
    elif response_code == 408:
        log_msg = f"408 Request Timeout: The server timed out waiting for the request. URL: {url}"
        logger.error(log_msg)
        raise TimeoutError(log_msg)
    elif response_code == 415:
        log_msg = f"415 Unsupported Media Type: The server does not support the media type of the request. URL: {url}"
        logger.error(log_msg)
        raise ValueError(log_msg)
    elif response_code == 429:
        log_msg = f"429 Too Many Requests: You have sent too many requests in a given amount of time. URL: {url}"
        logger.error(log_msg)
        raise RuntimeError(log_msg)
    elif response_code == 501:
        log_msg = f"501 Not Implemented: The server does not support the functionality required to fulfill the request. URL: {url}"
        logger.error(log_msg)
        raise NotImplementedError(log_msg)
    elif response_code == 500:
        log_msg = f"500 Internal Server Error: An error occurred on the server. URL: {url}"
        logger.error(log_msg)
        raise RuntimeError(log_msg)

class QiAuthentication():
    def __init__(self, username: str, server: str, password: str|None = None, protocol: str = "https", credentials_file: str|None = None, **kwargs):
        self.username = username
        self.password = password
        self.server = server
        self.username: str = username
        self.password: str|None = password
        self.server: str = server
        self.root_url: str = f"{protocol}://{self.server}/api"
        self.credentials_file: str|None = credentials_file
        self.use_keyring: bool = kwargs.get("use_keyring", False)
        self.keyring_service: str = kwargs.get("keyring_service", "pyQi")
        self.save_password_to_keyring = kwargs.get("save_password_to_keyring", False)

        if "log_level" in kwargs:
            log_level = kwargs.get("log_level", None)
        else:
            log_level = None
        try:
            log_level = getattr(logging, log_level.upper()) if log_level else logging.INFO
        except Exception:
            log_level = logging.INFO
        log_format = '%(asctime)s %(levelname)-8s [%(name)s] %(message)s'
        if "log_file" in kwargs:
            logging.basicConfig(level=log_level, filename=kwargs.get("log_file"), filemode='a', format=log_format)
        else:
            logging.basicConfig(level=log_level, format=log_format)
        logger.debug(f'Logging configured (level={logging.getLevelName(log_level)}, file={kwargs.get("log_file") or "stdout"})')

        self.auth = self.qi_login()
    
    def qi_login(self) -> HTTPBasicAuth:
        """
        Logs into Preservica. Either through manually logging in with credentials_file.
        """
        if self.credentials_file:
            logger.info('Using credentials file.')
            # Add Credentials File Handling Here
            logger.info(f'Successfully logged into Preservica Server {self.server}, as user: {self.username}')
            self.auth = HTTPBasicAuth(self.username, str(self.password))
            return self.auth
                    
        def _check_password(username: str, password: str|None) -> str:

            if None in (username, self.server):
                logger.exception('A Username or Server has not been provided... Please try again...')
                raise Exception('A Username or Server has not been provided... Please try again...')

            if password is None and self.save_password_to_keyring is False:
                password = self._get_password_from_keyring(username)
            
            if password is None:
                password = getpass(prompt=f"Please enter your password for QI for {username}: ")
                if self.save_password_to_keyring is True:
                    self._set_password_in_keyring(username, password)
            
            if password is not None:
                return password
            else:
                logger.exception('Password not provided and could not be retrieved from keyring. Please try again...')
                raise Exception('Password not provided and could not be retrieved from keyring. Please try again...')
        
        if self.username:
            self.password = _check_password(self.username, self.password)
        self.auth = HTTPBasicAuth(self.username, str(self.password))
        r = requests.get(self.root_url, auth=self.auth)  # Test the credentials by making a simple request
        _response_exception_handler(r.status_code, self.root_url)
        logger.info(f'Login test successful for user {self.username} on server {self.server}')
        return self.auth
    def test_login(self):
        """
        Test Login function, to ensure credentials are correct before running main.
        """
        try:
            self.qi_login()
            logger.info(f'Login successful: {self.server} as {self.username}')
        except Exception as e:
            log_msg = f'Login failed for user {self.username} on server {self.server}: {e}'
            logger.exception(log_msg)
            raise Exception(log_msg)
        
    def _keyring_entry_name(self) -> str:
        server = self.server or "default-server"
        return f"{self.keyring_service}:{server}"

    def _get_password_from_keyring(self, username) -> str|None:
        if not self.use_keyring:
            return None
        if keyring is None:
            raise RuntimeError("keyring package is not installed. Install with: pip install keyring")
        if not username or not self.server:
            return None
        try:
            return keyring.get_password(self._keyring_entry_name(), str(username))
        except KeyringError as e:
            logger.warning(f"Unable to read password from keyring: {e}")
            return None
        
    def _set_password_in_keyring(self, username: str, password: str) -> None:
        if not self.save_password_to_keyring:
            return
        if keyring is None:
            raise RuntimeError("keyring package is not installed. Install with: pip install keyring")
        if not self.username or not self.server:
            return
        try:
            keyring.set_password(self._keyring_entry_name(), str(username), password)
            logger.info("Password saved to keyring.")
        except KeyringError as e:
            log_msg = f"Unable to save password to keyring: {e}"
            logger.error(log_msg)
            raise KeyringError(log_msg)

class QiRecords():
    def __init__(self, json_data: dict):
        if json_data is None:
            logger.info('No results found')
            self.json_data = None
            self.total = 0
            self.records_list = []
            self.records = []
        else:
            self.json_data = json_data
            self.total = len(self.json_data['records'])
            self.records_list = []        
            if self.json_data is None:
                logger.info('No results found')
            else:
                logger.info(f'{self.total} records found, processing data...')
                for x in self.json_data['records']:
                    record_dict = {}
                    for y in x:
                        key = y
                        value = x[key]
                        record_dict[key] = value
                    self.records_list.append(record_dict)
                self.records = self._records_dict_to_obj()
                logger.debug(f"Records List: {self.records_list}")
                logger.info('Data processing complete.')

    def _records_dict_to_obj(self):
        record_list = []
        for record in self.records_list:
            rec = QiRecord(**record)
            record_list.append(rec)
        return record_list
            
    def json_to_file(self, output_file):
        with open(output_file, 'w') as f:
            json.dump(self.json_data, f)
    
    def json_tostring(self):
        json_string = json.dumps(self.json_data)
        return json_string
    
    def __str__(self):
        return f"QiRecords Object with {self.total} records. Use .records to access list of QiRecord objects.\n" \
               f"Records are dynamically generated based on the fields returned from the API, and can be accessed as attributes of each QiRecord object."
    
    def __repr__(self):
        return f"QiRecords Object with {self.total} records. Use .records to access list of QiRecord objects.\n" \
               f"Records are dynamically generated based on the fields returned from the API, and can be accessed as attributes of each QiRecord object."
    
    def to_dict(self):
        return self.json_data
    
    def to_json(self):
        return json.dumps(self.json_data)

class QiRecord():
    def __init__(self, **kwargs):
        for arg in kwargs.items():
            setattr(self,arg[0],arg[1])
    
    def __str__(self):
        return f"QiRecord Object with attributes: {', '.join(self.__dict__.keys())}"
    
    def __repr__(self) -> str:
        return f"QiRecord Object with attributes: {', '.join(self.__dict__.keys())}"
    
    def to_dict(self):
        return self.__dict__
    
    def to_json(self):
        return json.dumps(self.to_dict())