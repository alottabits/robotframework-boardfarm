*** Settings ***
Documentation     Example test suite demonstrating environment requirements.
...               
...               This suite shows how to use environment requirement tags
...               to conditionally run tests based on the testbed configuration.
...               
...               Tests with env_req tags will be skipped if the environment
...               doesn't match the requirement.

Library           BoardfarmLibrary

*** Test Cases ***
Test Dual Stack Requirement Using Tag
    [Documentation]    This test only runs in dual stack environments.
    [Tags]    env_req:dual_stack
    ${config}=    Get Boardfarm Config
    Log    Environment validated for dual stack
    Log Step    Dual stack environment verified

Test IPv4 Only Requirement Using Tag
    [Documentation]    This test only runs in IPv4 only environments.
    [Tags]    env_req:ipv4_only
    ${config}=    Get Boardfarm Config
    Log    Environment validated for IPv4 only
    Log Step    IPv4 only environment verified

Test IPv6 Only Requirement Using Tag
    [Documentation]    This test only runs in IPv6 only environments.
    [Tags]    env_req:ipv6_only
    ${config}=    Get Boardfarm Config
    Log    Environment validated for IPv6 only
    Log Step    IPv6 only environment verified

Test JSON Requirement In Tag
    [Documentation]    This test uses inline JSON for environment requirement.
    [Tags]    env_req:{"environment_def":{"board":{"eRouter_Provisioning_mode":["dual"]}}}
    ${config}=    Get Boardfarm Config
    Log    JSON environment requirement matched

Test Require Environment Keyword
    [Documentation]    This test uses the Require Environment keyword.
    Require Environment    dual_stack
    Log Step    Environment requirement validated via keyword

Test Require Environment With JSON
    [Documentation]    This test uses Require Environment with JSON.
    Require Environment    {"environment_def":{"board":{"eRouter_Provisioning_mode":["dual"]}}}
    Log Step    JSON environment requirement validated

Test Without Requirement
    [Documentation]    This test runs in any environment.
    ${config}=    Get Boardfarm Config
    Log    Test runs in any environment
    Log Step    No specific environment requirement
