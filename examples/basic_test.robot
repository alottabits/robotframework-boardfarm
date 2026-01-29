*** Settings ***
Documentation     Basic example test suite demonstrating robotframework-boardfarm usage.
...               
...               This suite shows how to access devices and configuration
...               using the BoardfarmLibrary keywords.
...               
...               Run with:
...               robot --listener robotframework_boardfarm.BoardfarmListener:board_name=my-board:env_config=./env.json:inventory_config=./inv.json examples/

Library           BoardfarmLibrary

Suite Setup       Log    Starting Boardfarm example tests
Suite Teardown    Log    Completed Boardfarm example tests

*** Test Cases ***
Test Device Manager Access
    [Documentation]    Verify we can access the device manager.
    ${dm}=    Get Device Manager
    Log    Device manager obtained: ${dm}

Test Device By Type
    [Documentation]    Verify we can get a device by type.
    ${cpe}=    Get Device By Type    CPE
    Log    CPE device: ${cpe}

Test Boardfarm Config
    [Documentation]    Verify we can access boardfarm configuration.
    ${config}=    Get Boardfarm Config
    Log    Boardfarm config: ${config}

Test Provisioning Mode
    [Documentation]    Verify we can get the provisioning mode.
    ${mode}=    Get Provisioning Mode
    Log    Provisioning mode: ${mode}

Test Device Config
    [Documentation]    Verify we can get device-specific config.
    ${board_config}=    Get Device Config    board
    Log    Board config: ${board_config}

Test Context Storage
    [Documentation]    Verify test context storage works.
    Set Test Context    test_key    test_value
    ${value}=    Get Test Context    test_key
    Should Be Equal    ${value}    test_value
    
    ${default}=    Get Test Context    missing_key    default_value
    Should Be Equal    ${default}    default_value
    
    Clear Test Context
    ${cleared}=    Get Test Context    test_key
    Should Be Equal    ${cleared}    ${NONE}

Test Log Step
    [Documentation]    Verify step logging works.
    Log Step    Step 1: Initialize test
    Log Step    Step 2: Perform action
    Log Step    Step 3: Verify result
