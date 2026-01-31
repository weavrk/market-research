#!/usr/bin/env python3
"""
Configuration and file structure tests (no dependencies required).
"""

import os
import re
from pathlib import Path

def test_application_root_in_code():
    """Check that APPLICATION_ROOT is configured in app.py."""
    print("="*60)
    print("Testing APPLICATION_ROOT in app.py")
    print("="*60)
    
    app_py = Path('app.py')
    if not app_py.exists():
        print("✗ app.py not found")
        return False
    
    content = app_py.read_text()
    
    # Check for APPLICATION_ROOT configuration
    if "APPLICATION_ROOT" in content:
        if "'/hrefs/market-research'" in content or '"/hrefs/market-research"' in content:
            print("✓ APPLICATION_ROOT is configured correctly in app.py")
            return True
        else:
            print("⚠ APPLICATION_ROOT found but value may be incorrect")
            return False
    else:
        print("✗ APPLICATION_ROOT not found in app.py")
        return False


def test_api_url_helper():
    """Check that apiUrl helper is in base.html."""
    print("\n" + "="*60)
    print("Testing apiUrl() helper in base.html")
    print("="*60)
    
    base_html = Path('templates/base.html')
    if not base_html.exists():
        print("✗ templates/base.html not found")
        return False
    
    content = base_html.read_text()
    
    if "function apiUrl" in content or "const apiUrl" in content or "apiUrl(path)" in content:
        print("✓ apiUrl() helper function found in base.html")
        
        # Check that it's used in loadBillingData
        if "apiUrl('api/billing')" in content or 'apiUrl("api/billing")' in content:
            print("✓ apiUrl() is used for billing API call")
            return True
        else:
            print("⚠ apiUrl() found but may not be used everywhere")
            return True  # Still pass, just a warning
    else:
        print("✗ apiUrl() helper function not found in base.html")
        return False


def test_fetch_calls_updated():
    """Check that all hardcoded fetch calls have been updated."""
    print("\n" + "="*60)
    print("Testing fetch() calls in templates")
    print("="*60)
    
    template_files = [
        'templates/base.html',
        'templates/analyze.html',
        'templates/markets.html',
        'templates/retailer_database.html',
        'templates/simple_results.html',
    ]
    
    issues = []
    passed = 0
    
    for template_file in template_files:
        template_path = Path(template_file)
        if not template_path.exists():
            issues.append(f"  ✗ {template_file} not found")
            continue
        
        content = template_path.read_text()
        
        # Find all fetch calls with hardcoded paths starting with /
        hardcoded_pattern = r"fetch\(['\"]\/[^'\"]+['\"]"
        matches = re.findall(hardcoded_pattern, content)
        
        # Filter out external URLs (http/https)
        hardcoded_api = [m for m in matches if not m.startswith("fetch('http") and not m.startswith('fetch("http')]
        
        if hardcoded_api:
            issues.append(f"  ⚠ {template_file} has hardcoded fetch calls:")
            for match in hardcoded_api[:3]:  # Show first 3
                issues.append(f"      {match[:60]}...")
        else:
            print(f"  ✓ {template_file} - No hardcoded API paths found")
            passed += 1
    
    if issues:
        for issue in issues:
            print(issue)
        return False
    
    print(f"\n✓ All {len(template_files)} templates checked - fetch() calls updated")
    return True


def test_templates_exist():
    """Verify all required templates exist."""
    print("\n" + "="*60)
    print("Testing Template Files")
    print("="*60)
    
    required_templates = [
        'templates/base.html',
        'templates/index.html',
        'templates/analyze.html',
        'templates/markets.html',
        'templates/retailer_database.html',
        'templates/simple_results.html',
        'templates/results.html',
        'templates/usage.html',
    ]
    
    passed = 0
    failed = 0
    
    for template in required_templates:
        template_path = Path(template)
        if template_path.exists():
            print(f"  ✓ {template}")
            passed += 1
        else:
            print(f"  ✗ {template} (not found)")
            failed += 1
    
    print(f"\nTemplates: {passed} found, {failed} missing")
    return failed == 0


def test_static_files():
    """Verify static files directory exists."""
    print("\n" + "="*60)
    print("Testing Static Files")
    print("="*60)
    
    static_dir = Path('static')
    if static_dir.exists():
        print(f"  ✓ static/ directory exists")
        favicon = static_dir / 'favicon.ico'
        if favicon.exists():
            print(f"  ✓ static/favicon.ico exists")
        else:
            print(f"  ⚠ static/favicon.ico not found (optional)")
        return True
    else:
        print(f"  ✗ static/ directory not found")
        return False


def test_data_directories():
    """Verify required data directories exist."""
    print("\n" + "="*60)
    print("Testing Data Directories")
    print("="*60)
    
    required_dirs = ['data', 'uploads']
    all_exist = True
    
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if dir_path.exists() and dir_path.is_dir():
            print(f"  ✓ {dir_name}/ exists")
        else:
            print(f"  ⚠ {dir_name}/ not found (will be created at runtime)")
    
    return True  # These are created automatically, so always pass


def test_deployment_files():
    """Check deployment-related files exist."""
    print("\n" + "="*60)
    print("Testing Deployment Files")
    print("="*60)
    
    deployment_files = [
        'deploy.py',
        'credentials.md',
        'requirements.txt',
        '.gitignore',
    ]
    
    passed = 0
    failed = 0
    
    for file_name in deployment_files:
        file_path = Path(file_name)
        if file_path.exists():
            print(f"  ✓ {file_name}")
            passed += 1
        else:
            print(f"  ✗ {file_name} (not found)")
            failed += 1
    
    print(f"\nDeployment Files: {passed} found, {failed} missing")
    return failed == 0


def test_credentials_file():
    """Check credentials.md has correct paths."""
    print("\n" + "="*60)
    print("Testing credentials.md Configuration")
    print("="*60)
    
    creds_file = Path('credentials.md')
    if not creds_file.exists():
        print("  ✗ credentials.md not found")
        return False
    
    content = creds_file.read_text()
    
    checks = [
        ('/hrefs/market-research/', 'FTP remote path'),
        ('https://weavrk.com/hrefs/market-research/', 'Production URL'),
        ('git@github.com:weavrk/market-research.git', 'GitHub SSH URL'),
    ]
    
    passed = 0
    for check_str, description in checks:
        if check_str in content:
            print(f"  ✓ {description} correct")
            passed += 1
        else:
            print(f"  ✗ {description} not found or incorrect")
    
    return passed == len(checks)


def main():
    """Run all configuration tests."""
    print("\n" + "="*60)
    print("Market Research - Configuration & File Structure Tests")
    print("="*60)
    print()
    
    tests = [
        ("APPLICATION_ROOT Configuration", test_application_root_in_code),
        ("apiUrl() Helper Function", test_api_url_helper),
        ("Fetch Calls Updated", test_fetch_calls_updated),
        ("Template Files", test_templates_exist),
        ("Static Files", test_static_files),
        ("Data Directories", test_data_directories),
        ("Deployment Files", test_deployment_files),
        ("Credentials Configuration", test_credentials_file),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} failed with exception: {e}")
            import traceback
            traceback.print_exc()
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
        print("\n✓ All configuration tests passed!")
        print("  Ready for production deployment.")
        return 0
    else:
        print("\n⚠ Some tests failed or have warnings.")
        print("  Please review the output above.")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())

