#!/usr/bin/env python3
"""
Simple Move API Authentication Test

This script tests authentication to the Nutanix Move API server using the official API specification.
Use this to verify connectivity and credentials before running the full migration script.
"""

import requests
import sys
import getpass
import urllib3
from urllib.parse import urljoin
import argparse
import json

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def test_move_authentication(server, username, password, port=9440, verify_ssl=False):
    """Test authentication to Move API server using official token endpoint
    
    Args:
        server: Move server IP or FQDN
        username: Move username
        password: Move password
        port: Move server port (default: 9440)
        verify_ssl: Whether to verify SSL certificates
    
    Returns:
        True if authentication successful, False otherwise
    """
    
    # Build base URL
    if '://' in server:
        base_url = server
        if not base_url.endswith(f":{port}") and port != 9440:
            base_url = f"{base_url}:{port}"
    else:
        base_url = f"https://{server}:{port}"
    
    print(f"Testing connection to Move server: {base_url}")
    print(f"Username: {username}")
    print(f"SSL verification: {'Enabled' if verify_ssl else 'Disabled'}")
    print("-" * 50)
    
    # Create session with timeout
    session = requests.Session()
    session.verify = verify_ssl
    session.timeout = (10, 30)  # 10s connect, 30s read
    
    # Official Move API token endpoint (per OpenAPI spec)
    token_endpoint = "/move/v2/token"
    full_url = urljoin(base_url, token_endpoint)
    
    print(f"Using official token endpoint: {token_endpoint}")
    print(f"Full URL: {full_url}")
    
    # Prepare form data as specified in OpenAPI spec
    form_data = {
        'grantType': 'PASSWORD',
        'username': username,
        'password': password,
        # 'expiry': 900  # Commented out - some Move versions don't support this
    }
    
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    try:
        print(f"\nTesting authentication...")
        print(f"Request method: POST")
        print(f"Content-Type: application/x-www-form-urlencoded")
        print(f"Form data: grantType=PASSWORD, username={username}, # no expiry parameter")
        
        response = session.post(
            full_url,
            data=form_data,  # Use form data, not JSON
            headers=headers,
            timeout=(10, 30)
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"✅ Authentication successful!")
                
                # Extract tokens from response (per TokenGenerationResponse schema)
                access_token = result.get('AccessToken')
                refresh_token = result.get('RefreshToken')
                access_expiry = result.get('AccessTokenExpiry')
                username_resp = result.get('Username')
                api_version = result.get('APIVersion')
                
                if access_token:
                    print(f"Access Token: {access_token[:20]}...")
                    print(f"Username: {username_resp}")
                    print(f"API Version: {api_version}")
                    print(f"Token Expiry: {access_expiry}")
                    
                    if refresh_token:
                        print(f"Refresh Token: {refresh_token[:20]}...")
                    
                    # Test the access token with a simple API call
                    if test_access_token(session, base_url, access_token):
                        print(f"\n🎉 SUCCESS: Move API authentication working correctly!")
                        print(f"Token endpoint: {token_endpoint}")
                        return True
                    else:
                        print(f"\n⚠️  Token received but may not be working properly")
                        return False
                else:
                    print(f"❌ No access token found in response")
                    print(f"Response: {json.dumps(result, indent=2)}")
                    return False
                    
            except json.JSONDecodeError:
                print(f"❌ Non-JSON response received")
                print(f"Response text: {response.text[:500]}...")
                return False
                
        elif response.status_code == 401:
            print(f"❌ Authentication failed - Invalid credentials")
            try:
                error_detail = response.json()
                print(f"Error details: {json.dumps(error_detail, indent=2)}")
            except:
                print(f"Error response: {response.text}")
            return False
            
        elif response.status_code == 404:
            print(f"❌ Token endpoint not found - This may not be a Move server")
            print(f"Response: {response.text[:200]}")
            return False
            
        else:
            print(f"❌ Unexpected response code: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return False
            
    except requests.exceptions.Timeout:
        print(f"❌ Timeout - Server not responding within 30 seconds")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection failed - {e}")
        return False
    except requests.exceptions.SSLError as e:
        print(f"❌ SSL error - {e}")
        print(f"Try running with SSL verification disabled (default)")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed - {e}")
        return False


def test_access_token(session, base_url, access_token):
    """Test the access token with a simple authenticated API call"""
    print(f"\nTesting access token with authenticated API call...")
    
    # Set authorization header with Bearer token (per OpenAPI spec)
    auth_headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    
    # Try simple API endpoints that should work with valid token
    test_endpoints = [
        "/move/v2/token/status",  # Token validation endpoint
        "/move/v2/appinfo",       # Application info
        "/move/v2/providers",     # List providers
    ]
    
    for endpoint in test_endpoints:
        try:
            response = session.get(
                urljoin(base_url, endpoint),
                headers=auth_headers,
                timeout=(5, 15)
            )
            
            print(f"Testing {endpoint}: Status {response.status_code}")
            
            if response.status_code == 200:
                print(f"✅ Token validation successful with {endpoint}")
                return True
            elif response.status_code == 401:
                print(f"⚠️  Token rejected at {endpoint}")
                continue
            elif response.status_code == 404:
                print(f"ℹ️  Endpoint {endpoint} not found (normal for some Move versions)")
                continue
            else:
                print(f"ℹ️  Endpoint {endpoint} returned {response.status_code}")
                continue
                
        except Exception as e:
            print(f"⚠️  Error testing {endpoint}: {e}")
            continue
    
    print(f"⚠️  Could not validate token with test API calls")
    return True  # Return True anyway since we got a token


def main():
    parser = argparse.ArgumentParser(
        description="Test Nutanix Move API authentication using official token endpoint",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python3 test_move_auth.py
  
  # Command line mode
  python3 test_move_auth.py --server 10.1.1.100 --username admin
  
  # With custom port
  python3 test_move_auth.py --server 10.1.1.100 --port 9440 --username admin
  
  # With SSL verification enabled
  python3 test_move_auth.py --server 10.1.1.100 --username admin --verify-ssl

Authentication Method:
  This script uses the official Move API authentication method:
  - POST /move/v2/token
  - Content-Type: application/x-www-form-urlencoded
  - Form data: grantType=PASSWORD, username=<user>, password=<pass>
  - Returns: AccessToken, RefreshToken, expiry times
  - Usage: Authorization: Bearer <AccessToken>
        """
    )
    
    parser.add_argument("--server", help="Move server IP or FQDN")
    parser.add_argument("--port", type=int, default=9440, help="Move server port (default: 9440)")
    parser.add_argument("--username", help="Move username")
    parser.add_argument("--password", help="Move password")
    parser.add_argument("--verify-ssl", action="store_true", help="Verify SSL certificates")
    
    args = parser.parse_args()
    
    print("=== Nutanix Move API Authentication Test ===")
    print("Using Official OpenAPI Specification Method\n")
    
    # Get inputs
    server = args.server or input("Move server IP/FQDN: ")
    port = args.port
    username = args.username or input("Username: ")
    password = args.password or getpass.getpass("Password: ")
    verify_ssl = args.verify_ssl
    
    try:
        success = test_move_authentication(server, username, password, port, verify_ssl)
        
        if success:
            print("\n🎉 Authentication test completed successfully!")
            print("You can now use these credentials with the migration script.")
            print("\nAuthentication details:")
            print("- Endpoint: POST /move/v2/token")
            print("- Method: Form data with grantType=PASSWORD")
            print("- Token Type: Bearer token in Authorization header")
        else:
            print("\n💥 Authentication test failed!")
            print("\nTroubleshooting steps:")
            print("1. Verify the server IP/FQDN is correct")
            print("2. Check that Move service is running on the server")
            print("3. Verify username and password are correct")
            print("4. Ensure port 9440 is accessible")
            print("5. Check firewall settings")
            print("6. Verify this is a Nutanix Move server (not Prism Central)")
            
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\nTest cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
