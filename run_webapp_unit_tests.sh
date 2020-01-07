#!/bin/bash

# Example: ./run_webapp_unit_tests.sh rosetta.base_app.tests.test_apis.ApiTests.test_api_web_auth

# You probably want to set DJANGO_LOG_LEVEL to ERROR and ROSETTA_LOG_LEVEL to DEBUG if you are doing tdd.
DJANGO_LOG_LEVEL="CRITICAL"
ROSETTA_LOG_LEVEL="CRITICAL"

rosetta/shell webapp "cd /opt/webapp_code && DJANGO_LOG_LEVEL=$DJANGO_LOG_LEVEL ROSETTA_LOG_LEVEL=$ROSETTA_LOG_LEVEL python3 manage.py test $@"
