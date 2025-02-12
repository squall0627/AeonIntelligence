import os
import typing
import json as json_lib
import httpx
from typing import Optional, Dict, Any

from httpx._types import RequestFiles

from nice_gui.state.user_state import user_state


class APIClient:
    def __init__(self, base_url: str = os.getenv("API_ENDPOINT")):
        self.base_url = base_url
        self.headers = {}

    def set_token(self, token: str, token_type: str = "Bearer"):
        """Set the authentication token for subsequent requests"""
        self.headers["Authorization"] = f"{token_type} {token}"

    async def get(
        self,
        endpoint: str,
        need_auth: bool = True,
        *,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict]:
        """Make a GET request to the API"""
        if need_auth:
            # Get auth token from storage
            auth = user_state.get_auth()
            if auth:
                auth_token = auth.access_token
                token_type = auth.token_type
                if auth_token:
                    # raise Exception("Not authenticated")
                    self.set_token(auth_token, token_type)
        else:
            self.headers.pop("Authorization", None)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}{endpoint}",
                    params=params,
                    headers=self.headers,
                    timeout=60,
                )

                if response.status_code == 401:
                    raise Exception("Authentication expired")
                elif response.status_code == 403:
                    raise Exception("Permission denied")
                elif response.status_code == 422:
                    raise Exception("Invalid request format")
                elif response.status_code == 200:
                    return response.json()
                else:
                    raise Exception(f"API error: {response.status_code}")
            return None
        except httpx.RequestError as e:
            raise Exception(f"API error: {str(e)}")

    async def post(
        self,
        endpoint: str,
        need_auth: bool = True,
        *,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[typing.Any] = None,
        files: Optional[RequestFiles] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict]:
        """Make a POST request to the API"""

        # validate params
        data, json, files = self.params_validation(data, json, files)

        if need_auth:
            # Get auth token from storage
            auth = user_state.get_auth()
            if auth:
                auth_token = auth.access_token
                token_type = auth.token_type
                if auth_token:
                    # raise Exception("Not authenticated")
                    self.set_token(auth_token, token_type)
        else:
            self.headers.pop("Authorization", None)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}{endpoint}",
                    data=data,
                    json=json,
                    files=files,
                    params=params,
                    headers=self.headers,
                    timeout=300,
                )

                if response.status_code == 401:
                    raise Exception("Authentication expired")
                elif response.status_code == 403:
                    raise Exception("Permission denied")
                elif response.status_code == 422:
                    raise Exception("Invalid request format")
                elif response.status_code == 200:
                    return response.json()
                else:
                    raise Exception(f"API error: {response.status_code}")
            return None
        except httpx.RequestError as e:
            raise Exception(f"API error: {str(e)}")

    async def post_streaming(
        self,
        endpoint: str,
        need_auth: bool = True,
        *,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[typing.Any] = None,
        files: Optional[RequestFiles] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> typing.AsyncGenerator[str, None]:
        """Make a POST request to the API"""

        # validate params
        data, json, files = self.params_validation(data, json, files)

        if need_auth:
            # Get auth token from storage
            auth = user_state.get_auth()
            if auth:
                auth_token = auth.access_token
                token_type = auth.token_type
                if auth_token:
                    # raise Exception("Not authenticated")
                    self.set_token(auth_token, token_type)
        else:
            self.headers.pop("Authorization", None)

        # Add is_stream flag
        if data is not None:
            if "params" in data:
                params = json_lib.loads(data["params"])
                params.update({"is_stream": True})
                data.update({"params": json_lib.dumps(params)})
        if json is not None:
            json.update({"is_stream": True})

        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}{endpoint}",
                    data=data,
                    json=json,
                    files=files,
                    params=params,
                    headers=self.headers,
                    timeout=300,
                ) as response:
                    if response.status_code == 401:
                        raise Exception("Authentication expired")
                    elif response.status_code == 403:
                        raise Exception("Permission denied")
                    elif response.status_code == 422:
                        raise Exception("Invalid request format")
                    elif response.status_code == 200:
                        async for chunk in response.aiter_text():
                            if chunk:
                                # Process each chunk from the stream
                                yield chunk
                    else:
                        raise Exception(f"API error: {response.status_code}")
        except httpx.RequestError as e:
            raise Exception(f"API error: {str(e)}")
        except Exception as e:
            raise Exception(f"Other exception: {str(e)}")

    def params_validation(
        self,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[typing.Any] = None,
        files: Optional[RequestFiles] = None,
    ) -> (Optional[Dict[str, Any]], Optional[typing.Any], Optional[RequestFiles]):
        if data is not None and json is not None:
            raise Exception("Cannot use both data and json in the same request")
        if files is not None and json is not None:
            # Convert json to form data
            if data:
                data.update({"params": json_lib.dumps(json)})
            else:
                data = {"params": json_lib.dumps(json)}
            json = None
        return data, json, files

    async def get_file(
        self,
        endpoint: str,
        need_auth: bool = True,
        *,
        params: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        """Make a GET File request to the API"""
        if need_auth:
            # Get auth token from storage
            auth = user_state.get_auth()
            if auth:
                auth_token = auth.access_token
                token_type = auth.token_type
                if auth_token:
                    # raise Exception("Not authenticated")
                    self.set_token(auth_token, token_type)
        else:
            self.headers.pop("Authorization", None)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}{endpoint}",
                    params=params,
                    headers=self.headers,
                    timeout=300,
                )

                if response.status_code == 401:
                    raise Exception("Authentication expired")
                elif response.status_code == 403:
                    raise Exception("Permission denied")
                elif response.status_code == 422:
                    raise Exception("Invalid request format")
                elif response.status_code == 200:
                    return response.read()
                else:
                    raise Exception(f"File download error: {response.status_code}")
        except httpx.RequestError as e:
            raise Exception(f"File download error: {str(e)}")
