"""
Mock data for SCA Vulnerabilities Scanning app.
Structure: one row per repo + library combination
"""

import pandas as pd
from datetime import datetime, timedelta
import random

def get_mock_repos() -> pd.DataFrame:
    """
    Get mock vulnerable libraries (one row per repo + library).
    
    Returns:
        DataFrame with vulnerability counts per candidate version
    """
    
    data = {
        'repo_path': [
            '/repos/payment-gateway-api',
            '/repos/frontend-dashboard',
            '/repos/frontend-dashboard',
            '/repos/audit-logging',
            '/repos/config-manager',
            '/repos/user-service-v2',
            '/repos/data-processor',
            '/repos/data-processor',
            '/repos/api-gateway',
            '/repos/admin-portal'
        ],
        'library': [
            'requests',
            'lodash',
            'axios',
            'log4j',
            'PyYAML',
            'axios',
            'jackson-databind',
            'commons-io',
            'body-parser',
            'django'
        ],
        'current_version': [
            '2.6.0',
            '4.17.15',
            '0.21.1',
            '2.14.1',
            '5.3.1',
            '0.21.1',
            '2.9.8',
            '2.4',
            '1.19.0',
            '2.2.10'
        ],
        'repo_name': [
            'payment-gateway-api',
            'frontend-dashboard',
            'frontend-dashboard',
            'audit-logging-service',
            'config-manager',
            'user-service-v2',
            'data-processor',
            'data-processor',
            'api-gateway',
            'admin-portal'
        ],
        'repo_url': [
            'https://github.com/company/payment-gateway-api',
            'https://github.com/company/frontend-dashboard',
            'https://github.com/company/frontend-dashboard',
            'https://github.com/company/audit-logging-service',
            'https://github.com/company/config-manager',
            'https://github.com/company/user-service-v2',
            'https://github.com/company/data-processor',
            'https://github.com/company/data-processor',
            'https://github.com/company/api-gateway',
            'https://github.com/company/admin-portal'
        ],
        'priority': [
            'Critical',
            'Critical',
            'High',
            'Critical',
            'High',
            'High',
            'Critical',
            'Medium',
            'Medium',
            'High'
        ],
        'cve_ids': [
            ['CVE-2023-32681'],
            ['CVE-2021-23337'],
            ['CVE-2021-3749'],
            ['CVE-2021-44228', 'CVE-2021-45046'],
            ['CVE-2020-14343'],
            ['CVE-2021-3749'],
            ['CVE-2020-36518'],
            ['CVE-2021-29425'],
            ['CVE-2022-29078'],
            ['CVE-2021-35042']
        ],
        'cvss_score': [
            7.5,
            8.1,
            7.5,
            10.0,
            9.8,
            7.5,
            8.1,
            7.0,
            7.5,
            7.4
        ],
        'candidate_versions': [
            [{'version': '2.31.0', 'vulnerability_count': 0, 'release_date': datetime(2024, 5, 20), 'detected_ts': datetime(2026, 2, 4, 14, 23)},
             {'version': '2.28.2', 'vulnerability_count': 0, 'release_date': datetime(2023, 12, 10), 'detected_ts': datetime(2026, 2, 4, 14, 23)},
             {'version': '2.27.1', 'vulnerability_count': 1, 'release_date': datetime(2023, 1, 15), 'detected_ts': datetime(2026, 2, 4, 14, 23)},
             {'version': '2.26.0', 'vulnerability_count': 2, 'release_date': datetime(2022, 3, 8), 'detected_ts': datetime(2026, 2, 4, 14, 23)}],
            [{'version': '4.17.21', 'vulnerability_count': 0, 'release_date': datetime(2024, 2, 10), 'detected_ts': datetime(2026, 2, 4, 10, 15)},
             {'version': '4.17.20', 'vulnerability_count': 0, 'release_date': datetime(2023, 8, 25), 'detected_ts': datetime(2026, 2, 4, 10, 15)},
             {'version': '4.17.19', 'vulnerability_count': 1, 'release_date': datetime(2022, 11, 12), 'detected_ts': datetime(2026, 2, 4, 10, 15)}],
            [{'version': '1.6.0', 'vulnerability_count': 0, 'release_date': datetime(2024, 3, 14), 'detected_ts': datetime(2026, 2, 4, 10, 15)},
             {'version': '1.2.0', 'vulnerability_count': 1, 'release_date': datetime(2023, 6, 20), 'detected_ts': datetime(2026, 2, 4, 10, 15)},
             {'version': '0.27.2', 'vulnerability_count': 2, 'release_date': datetime(2022, 9, 5), 'detected_ts': datetime(2026, 2, 4, 10, 15)},
             {'version': '0.26.1', 'vulnerability_count': 3, 'release_date': datetime(2021, 12, 1), 'detected_ts': datetime(2026, 2, 4, 10, 15)}],
            [{'version': '2.20.0', 'vulnerability_count': 0, 'release_date': datetime(2024, 1, 15), 'detected_ts': datetime(2026, 2, 3, 16, 45)},
             {'version': '2.17.1', 'vulnerability_count': 0, 'release_date': datetime(2023, 12, 10), 'detected_ts': datetime(2026, 2, 3, 16, 45)},
             {'version': '2.16.0', 'vulnerability_count': 1, 'release_date': datetime(2023, 5, 22), 'detected_ts': datetime(2026, 2, 3, 16, 45)},
             {'version': '2.15.0', 'vulnerability_count': 2, 'release_date': datetime(2022, 8, 30), 'detected_ts': datetime(2026, 2, 3, 16, 45)}],
            [{'version': '6.0', 'vulnerability_count': 0, 'release_date': datetime(2024, 4, 18), 'detected_ts': datetime(2026, 2, 3, 9, 30)},
             {'version': '5.4.1', 'vulnerability_count': 0, 'release_date': datetime(2023, 7, 8), 'detected_ts': datetime(2026, 2, 3, 9, 30)},
             {'version': '5.4', 'vulnerability_count': 1, 'release_date': datetime(2023, 3, 12), 'detected_ts': datetime(2026, 2, 3, 9, 30)},
             {'version': '5.3.2', 'vulnerability_count': 2, 'release_date': datetime(2022, 10, 5), 'detected_ts': datetime(2026, 2, 3, 9, 30)}],
            [{'version': '1.6.0', 'vulnerability_count': 0, 'release_date': datetime(2024, 3, 14), 'detected_ts': datetime(2026, 2, 2, 13, 20)},
             {'version': '1.2.0', 'vulnerability_count': 1, 'release_date': datetime(2023, 6, 20), 'detected_ts': datetime(2026, 2, 2, 13, 20)},
             {'version': '0.27.2', 'vulnerability_count': 2, 'release_date': datetime(2022, 9, 5), 'detected_ts': datetime(2026, 2, 2, 13, 20)}],
            [{'version': '2.15.0', 'vulnerability_count': 0, 'release_date': datetime(2024, 6, 5), 'detected_ts': datetime(2026, 2, 2, 11, 10)},
             {'version': '2.14.2', 'vulnerability_count': 1, 'release_date': datetime(2023, 11, 18), 'detected_ts': datetime(2026, 2, 2, 11, 10)},
             {'version': '2.13.4', 'vulnerability_count': 2, 'release_date': datetime(2023, 4, 22), 'detected_ts': datetime(2026, 2, 2, 11, 10)},
             {'version': '2.12.7', 'vulnerability_count': 3, 'release_date': datetime(2022, 7, 9), 'detected_ts': datetime(2026, 2, 2, 11, 10)}],
            [{'version': '2.11.0', 'vulnerability_count': 0, 'release_date': datetime(2024, 7, 12), 'detected_ts': datetime(2026, 2, 2, 11, 10)},
             {'version': '2.8.0', 'vulnerability_count': 0, 'release_date': datetime(2023, 9, 3), 'detected_ts': datetime(2026, 2, 2, 11, 10)},
             {'version': '2.7', 'vulnerability_count': 1, 'release_date': datetime(2022, 12, 15), 'detected_ts': datetime(2026, 2, 2, 11, 10)}],
            [{'version': '1.20.2', 'vulnerability_count': 0, 'release_date': datetime(2024, 8, 20), 'detected_ts': datetime(2026, 2, 1, 15, 0)},
             {'version': '1.20.1', 'vulnerability_count': 0, 'release_date': datetime(2024, 1, 25), 'detected_ts': datetime(2026, 2, 1, 15, 0)},
             {'version': '1.20.0', 'vulnerability_count': 1, 'release_date': datetime(2023, 10, 10), 'detected_ts': datetime(2026, 2, 1, 15, 0)}],
            [{'version': '3.2.20', 'vulnerability_count': 0, 'release_date': datetime(2024, 9, 1), 'detected_ts': datetime(2026, 1, 31, 14, 30)},
             {'version': '3.2.13', 'vulnerability_count': 0, 'release_date': datetime(2024, 3, 5), 'detected_ts': datetime(2026, 1, 31, 14, 30)},
             {'version': '2.2.28', 'vulnerability_count': 1, 'release_date': datetime(2023, 2, 18), 'detected_ts': datetime(2026, 1, 31, 14, 30)},
             {'version': '3.1.14', 'vulnerability_count': 2, 'release_date': datetime(2022, 6, 7), 'detected_ts': datetime(2026, 1, 31, 14, 30)}]
        ],
        'last_detected_ts': [
            datetime(2026, 2, 4, 14, 23),
            datetime(2026, 2, 4, 10, 15),
            datetime(2026, 2, 4, 10, 15),
            datetime(2026, 2, 3, 16, 45),
            datetime(2026, 2, 3, 9, 30),
            datetime(2026, 2, 2, 13, 20),
            datetime(2026, 2, 2, 11, 10),
            datetime(2026, 2, 2, 11, 10),
            datetime(2026, 2, 1, 15, 0),
            datetime(2026, 1, 31, 14, 30)
        ],
        'status': [
            'ready', 'ready', 'ready', 'ready', 'ready',
            'analyzing', 'ready', 'ready', 'ready', 'analyzing'
        ]
    }
    
    return pd.DataFrame(data)


def get_mock_agent_analysis(repo_path: str, library: str, old_version: str, new_version: str) -> dict:
    """
    Get mock agent analysis results for a library upgrade.
    
    Returns:
        Dict with files_impacted, lines_changed, file_diffs, generated_ts
    """
    
    # Mock analysis based on library
    analyses = {
        'requests': {
            'files_impacted': 3,
            'lines_changed': 15,
            'file_diffs': {
                'src/api/client.py': {
                    'old_code': '''import requests
from config import API_URL

def fetch_data(endpoint):
    # Vulnerable: no timeout, verify=False
    response = requests.get(
        f"{API_URL}/{endpoint}",
        verify=False
    )
    return response.json()

def post_data(endpoint, payload):
    response = requests.post(
        f"{API_URL}/{endpoint}",
        json=payload,
        verify=False
    )
    return response.json()
''',
                    'new_code': '''import requests
from config import API_URL

def fetch_data(endpoint):
    # Fixed: added timeout and proper SSL verification
    response = requests.get(
        f"{API_URL}/{endpoint}",
        verify=True,
        timeout=30
    )
    return response.json()

def post_data(endpoint, payload):
    response = requests.post(
        f"{API_URL}/{endpoint}",
        json=payload,
        verify=True,
        timeout=30
    )
    return response.json()
'''
                },
                'tests/test_api.py': {
                    'old_code': '''import unittest
from src.api.client import fetch_data

class TestAPI(unittest.TestCase):
    def test_fetch(self):
        result = fetch_data("users")
        self.assertIsNotNone(result)
''',
                    'new_code': '''import unittest
from src.api.client import fetch_data

class TestAPI(unittest.TestCase):
    def test_fetch(self):
        result = fetch_data("users")
        self.assertIsNotNone(result)
'''
                },
                'requirements.txt': {
                    'old_code': f'requests=={old_version}\nflask==2.0.1\n',
                    'new_code': f'requests=={new_version}\nflask==2.0.1\n'
                }
            }
        },
        'lodash': {
            'files_impacted': 5,
            'lines_changed': 22,
            'file_diffs': {
                'src/utils/helpers.js': {
                    'old_code': '''import _ from 'lodash';

export function processData(data) {
    // Vulnerable: prototype pollution
    return _.merge({}, data);
}

export function cloneData(data) {
    return _.clone(data);
}
''',
                    'new_code': '''import _ from 'lodash';

export function processData(data) {
    // Fixed: safe merge
    return _.mergeWith({}, data, (objValue, srcValue) => {
        if (_.isArray(objValue)) return srcValue;
    });
}

export function cloneData(data) {
    return _.cloneDeep(data);
}
'''
                },
                'package.json': {
                    'old_code': f'''{{"dependencies": {{"lodash": "^{old_version}"}}}}''',
                    'new_code': f'''{{"dependencies": {{"lodash": "^{new_version}"}}}}'''
                }
            }
        },
        'log4j': {
            'files_impacted': 2,
            'lines_changed': 8,
            'file_diffs': {
                'pom.xml': {
                    'old_code': f'''    <dependency>
        <groupId>org.apache.logging.log4j</groupId>
        <artifactId>log4j-core</artifactId>
        <version>{old_version}</version>
    </dependency>
''',
                    'new_code': f'''    <dependency>
        <groupId>org.apache.logging.log4j</groupId>
        <artifactId>log4j-core</artifactId>
        <version>{new_version}</version>
    </dependency>
'''
                }
            }
        }
    }
    
    # Get analysis or generate generic one
    analysis = analyses.get(library, {
        'files_impacted': random.randint(2, 4),
        'lines_changed': random.randint(8, 20),
        'file_diffs': {
            f'{library.lower()}-dependency.txt': {
                'old_code': f'{library}=={old_version}\n',
                'new_code': f'{library}=={new_version}\n'
            }
        }
    })
    
    analysis['generated_ts'] = datetime.now()
    
    return analysis
