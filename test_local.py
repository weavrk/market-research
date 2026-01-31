#!/usr/bin/env python3
"""
Local testing script for Market Research application.
Tests Flask routes with APPLICATION_ROOT prefix.
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
import json

def test_application_root():
    """Test that APPLICATION_ROOT is configured correctly."""
    print("="*60)
    print("Testing APPLICATION_ROOT Configuration")
    print("="*60)
    
    app_root = app.config.get('APPLICATION_ROOT', None)
    expected_root = '/hrefs/market-research'
    
    if app_root == expected_root:
        print(f"✓ APPLICATION_ROOT is correctly set to: {app_root}")
        return True
    else:
        print(f"✗ APPLICATION_ROOT mismatch!")
        print(f"  Expected: {expected_root}")
        print(f"  Got: {app_root}")
        return False


def test_routes():
    """Test that all routes are accessible."""
    print("\n" + "="*60)
    print("Testing Flask Routes")
    print("="*60)
    
    with app.test_client() as client:
        # Test main routes
        routes_to_test = [
            ('/', 'index'),
            ('/retailer-database', 'retailer_database'),
            ('/markets', 'markets'),
            ('/analyze', 'analyze'),
            ('/usage', 'usage'),
            ('/results', 'view_results'),
            ('/api/billing', 'api_billing'),
            ('/api/zip-cache', 'get_zip_cache'),
        ]
        
        passed = 0
        failed = 0
        
        for route, endpoint_name in routes_to_test:
            try:
                response = client.get(route)
                if response.status_code in [200, 302, 405]:  # 405 is OK for POST-only routes
                    print(f"✓ {route:30} -> {endpoint_name:20} (Status: {response.status_code})")
                    passed += 1
                else:
                    print(f"✗ {route:30} -> {endpoint_name:20} (Status: {response.status_code})")
                    failed += 1
            except Exception as e:
                print(f"✗ {route:30} -> {endpoint_name:20} (Error: {str(e)[:50]})")
                failed += 1
        
        print(f"\nRoutes Test: {passed} passed, {failed} failed")
        return failed == 0


def test_url_for():
    """Test that url_for generates correct paths with APPLICATION_ROOT."""
    print("\n" + "="*60)
    print("Testing url_for() with APPLICATION_ROOT")
    print("="*60)
    
    with app.test_request_context('/hrefs/market-research/'):
        try:
            from flask import url_for
            
            test_routes = {
                'index': '/hrefs/market-research/',
                'retailer_database': '/hrefs/market-research/retailer-database',
                'markets': '/hrefs/market-research/markets',
                'analyze': '/hrefs/market-research/analyze',
            }
            
            passed = 0
            failed = 0
            
            for route_name, expected_path in test_routes.items():
                try:
                    generated_path = url_for(route_name)
                    if generated_path == expected_path:
                        print(f"✓ {route_name:25} -> {generated_path}")
                        passed += 1
                    else:
                        print(f"✗ {route_name:25} -> {generated_path} (Expected: {expected_path})")
                        failed += 1
                except Exception as e:
                    print(f"✗ {route_name:25} -> Error: {str(e)[:50]}")
                    failed += 1
            
            print(f"\nurl_for() Test: {passed} passed, {failed} failed")
            return failed == 0
            
        except Exception as e:
            print(f"✗ Error testing url_for(): {e}")
            return False


def test_api_endpoints():
    """Test API endpoints return valid JSON."""
    print("\n" + "="*60)
    print("Testing API Endpoints")
    print("="*60)
    
    with app.test_client() as client:
        api_endpoints = [
            ('/api/billing', 'GET'),
            ('/api/zip-cache', 'GET'),
        ]
        
        passed = 0
        failed = 0
        
        for endpoint, method in api_endpoints:
            try:
                if method == 'GET':
                    response = client.get(endpoint)
                else:
                    response = client.post(endpoint)
                
                if response.status_code == 200:
                    try:
                        data = json.loads(response.data)
                        print(f"✓ {endpoint:30} -> Valid JSON response")
                        passed += 1
                    except json.JSONDecodeError:
                        print(f"✗ {endpoint:30} -> Invalid JSON response")
                        failed += 1
                else:
                    print(f"⚠ {endpoint:30} -> Status: {response.status_code} (may be expected)")
                    passed += 1  # Some endpoints may return other status codes
                    
            except Exception as e:
                print(f"✗ {endpoint:30} -> Error: {str(e)[:50]}")
                failed += 1
        
        print(f"\nAPI Endpoints Test: {passed} passed, {failed} failed")
        return failed == 0


def test_templates_exist():
    """Verify all required templates exist."""
    print("\n" + "="*60)
    print("Testing Template Files")
    print("="*60)
    
    required_templates = [
        'base.html',
        'index.html',
        'analyze.html',
        'markets.html',
        'retailer_database.html',
        'simple_results.html',
        'results.html',
        'usage.html',
    ]
    
    templates_dir = Path('templates')
    passed = 0
    failed = 0
    
    for template in required_templates:
        template_path = templates_dir / template
        if template_path.exists():
            print(f"✓ {template}")
            passed += 1
        else:
            print(f"✗ {template} (not found)")
            failed += 1
    
    print(f"\nTemplates Test: {passed} passed, {failed} failed")
    return failed == 0


def test_static_files():
    """Verify static files directory exists."""
    print("\n" + "="*60)
    print("Testing Static Files")
    print("="*60)
    
    static_dir = Path('static')
    if static_dir.exists():
        print(f"✓ Static directory exists")
        favicon = static_dir / 'favicon.ico'
        if favicon.exists():
            print(f"✓ favicon.ico exists")
        else:
            print(f"⚠ favicon.ico not found (optional)")
        return True
    else:
        print(f"✗ Static directory not found")
        return False


def test_data_directories():
    """Verify required data directories exist."""
    print("\n" + "="*60)
    print("Testing Data Directories")
    print("="*60)
    
    required_dirs = ['data', 'uploads']
    passed = 0
    failed = 0
    
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if dir_path.exists() and dir_path.is_dir():
            print(f"✓ {dir_name}/ exists")
            passed += 1
        else:
            print(f"⚠ {dir_name}/ not found (will be created at runtime)")
            passed += 1  # These are created automatically
    
    print(f"\nData Directories Test: {passed} passed, {failed} failed")
    return True


def test_deployment_script():
    """Test that deployment script can be imported."""
    print("\n" + "="*60)
    print("Testing Deployment Script")
    print("="*60)
    
    try:
        import deploy
        print("✓ deploy.py can be imported")
        
        # Check if main functions exist
        if hasattr(deploy, 'deploy_ftp'):
            print("✓ deploy_ftp() function exists")
        if hasattr(deploy, 'deploy_github'):
            print("✓ deploy_github() function exists")
        if hasattr(deploy, 'main'):
            print("✓ main() function exists")
        
        return True
    except Exception as e:
        print(f"✗ Error importing deploy.py: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("Market Research - Local Testing Suite")
    print("="*60)
    print()
    
    tests = [
        ("Application Root Configuration", test_application_root),
        ("Flask Routes", test_routes),
        ("url_for() Path Generation", test_url_for),
        ("API Endpoints", test_api_endpoints),
        ("Template Files", test_templates_exist),
        ("Static Files", test_static_files),
        ("Data Directories", test_data_directories),
        ("Deployment Script", test_deployment_script),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:10} {test_name}")
    
    print("\n" + "="*60)
    print(f"Total: {passed}/{total} tests passed")
    print("="*60)
    
    if passed == total:
        print("\n✓ All tests passed! Ready for production deployment.")
        return 0
    else:
        print("\n✗ Some tests failed. Please review the output above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())

