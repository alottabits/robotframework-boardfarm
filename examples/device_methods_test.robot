*** Settings ***
Documentation     Example demonstrating dynamic keyword discovery
...               for both testbed infrastructure and device methods.
...
...               BoardfarmLibrary: Introspects DeviceManager, BoardfarmConfig
...               DeviceMethodLibrary: Introspects device instances and components
...
...               Run with:
...               robot --listener robotframework_boardfarm.BoardfarmListener:board_name=my-board:env_config=./env.json:inventory_config=./inv.json examples/device_methods_test.robot

# Testbed infrastructure (introspects DeviceManager, BoardfarmConfig)
Library           BoardfarmLibrary

# Device methods (introspects device instances) - one per device type
Library           DeviceMethodLibrary    device_type=ACS    WITH NAME    ACS
Library           DeviceMethodLibrary    device_type=CPE    WITH NAME    CPE

*** Variables ***
${PARAM_MANUFACTURER}    Device.DeviceInfo.Manufacturer
${PARAM_MODEL}           Device.DeviceInfo.ModelName
${PARAM_UPTIME}          Device.DeviceInfo.UpTime

*** Test Cases ***
#=============================================================================
# BOARDFARM LIBRARY: Testbed Infrastructure
#=============================================================================

Test DeviceManager Methods
    [Documentation]    Keywords discovered from DeviceManager instance.
    ...                Prefix: Dm
    [Tags]    testbed    device-manager

    # Utility keyword (resolves device type from string)
    ${cpe}=    Get Device By Type    CPE
    ${acs}=    Get Device By Type    ACS
    Log    Got CPE and ACS devices via utility keyword

    # Get device manager for direct access
    ${dm}=    Get Device Manager
    Log    Device manager: ${dm}

Test BoardfarmConfig Methods
    [Documentation]    Keywords discovered from BoardfarmConfig instance.
    ...                Prefix: Config
    [Tags]    testbed    config

    # Dynamically discovered from BoardfarmConfig
    ${mode}=    Config Get Prov Mode
    Log    Provisioning mode: ${mode}

    # More config methods (discovered at runtime)
    ${config}=    Get Boardfarm Config
    Log    Config object: ${config}

Test Utility Keywords
    [Documentation]    Robot Framework specific utilities.
    [Tags]    testbed    utilities

    # Logging
    Log Step    Step 1: Initialize test
    Log Step    Step 2: Perform action

    # Context storage
    Set Test Context    original_value    12345
    ${value}=    Get Test Context    original_value
    Should Be Equal    ${value}    12345

    # Clear context
    Clear Test Context
    ${value}=    Get Test Context    original_value    default
    Should Be Equal    ${value}    default

#=============================================================================
# DEVICE METHOD LIBRARY: Device Instance Methods
#=============================================================================

Test ACS NBI Methods
    [Documentation]    Keywords discovered from acs.nbi component.
    ...                Prefix: Nbi
    [Tags]    device    acs    nbi

    # GPV - GetParameterValues (discovered from acs.nbi.GPV)
    ${result}=    ACS.Nbi GPV    ${PARAM_MANUFACTURER}
    Log    Manufacturer: ${result[0]['value']}

    # Get multiple parameters
    @{params}=    Create List    ${PARAM_MANUFACTURER}    ${PARAM_MODEL}
    ${result}=    ACS.Nbi GPV    ${params}
    FOR    ${param}    IN    @{result}
        Log    ${param['key']}: ${param['value']}
    END

    # GPN - GetParameterNames (discovered from acs.nbi.GPN)
    ${names}=    ACS.Nbi GPN    Device.DeviceInfo.    next_level=${TRUE}
    Log    Found ${names.__len__()} parameters

    # GetRPCMethods (discovered from acs.nbi.GetRPCMethods)
    ${methods}=    ACS.Nbi Get RPC Methods
    Log    Available RPC methods: ${methods}

Test CPE SW Methods
    [Documentation]    Keywords discovered from cpe.sw component.
    ...                Prefix: Sw
    [Tags]    device    cpe    sw

    # Get uptime (discovered from cpe.sw.get_seconds_uptime)
    ${uptime}=    CPE.Sw Get Seconds Uptime
    Log    CPE uptime: ${uptime} seconds
    Should Be True    ${uptime} > 0

    # Check online status (discovered from cpe.sw.is_online)
    ${online}=    CPE.Sw Is Online
    Log    CPE online: ${online}
    Should Be True    ${online}

    # Get provisioning mode (discovered from cpe.sw.get_provision_mode)
    ${mode}=    CPE.Sw Get Provision Mode
    Log    Provision mode: ${mode}

    # Check TR-069 connection (discovered from cpe.sw.is_tr069_connected)
    ${connected}=    CPE.Sw Is Tr069 Connected
    Log    TR-069 connected: ${connected}

Test Generic Method Access
    [Documentation]    Generic fallback for maximum flexibility.
    [Tags]    device    generic

    # Call any method via generic keyword
    ${result}=    ACS.Call Device Method    ACS    nbi.GPV    ${PARAM_UPTIME}
    Log    Uptime via generic: ${result[0]['value']}

    # Call CPE method via generic keyword
    ${uptime}=    CPE.Call Device Method    CPE    sw.get_seconds_uptime
    Log    Uptime via generic: ${uptime}

    # Call with component specification
    ${result}=    ACS.Call Component Method    ACS    nbi    GPN    Device.    next_level=${TRUE}
    Log    GPN via component method

#=============================================================================
# COMBINED: Real Test Scenario
#=============================================================================

Test End To End Device Verification
    [Documentation]    Combining testbed and device method keywords.
    [Tags]    e2e

    Log Step    Verifying device connectivity

    # Testbed: Get provisioning mode from config
    ${mode}=    Config Get Prov Mode
    Log    Environment provisioning mode: ${mode}

    # Device: CPE status check
    ${online}=    CPE.Sw Is Online
    Should Be True    ${online}    CPE must be online

    Log Step    Retrieving device information via TR-069

    # Device: TR-069 operations
    @{info_params}=    Create List
    ...    Device.DeviceInfo.Manufacturer
    ...    Device.DeviceInfo.ModelName
    ...    Device.DeviceInfo.SoftwareVersion
    ${info}=    ACS.Nbi GPV    ${info_params}

    FOR    ${param}    IN    @{info}
        Log    ${param['key']}: ${param['value']}
    END

    Log Step    Verifying device state consistency

    # Compare TR-069 reported uptime with CPE uptime
    ${tr069_uptime}=    ACS.Nbi GPV    ${PARAM_UPTIME}
    ${cpe_uptime}=    CPE.Sw Get Seconds Uptime

    ${tr069_value}=    Convert To Number    ${tr069_uptime[0]['value']}
    ${diff}=    Evaluate    abs(${tr069_value} - ${cpe_uptime})
    Should Be True    ${diff} < 10    Uptime values should be within 10 seconds

    Log Step    Device verification complete

#=============================================================================
# FUTURE-PROOFING: Automatic Adaptation
#=============================================================================

Test Future Proofing
    [Documentation]    Both libraries auto-adapt when Boardfarm evolves.
    [Tags]    future

    # When Boardfarm adds new methods, they're immediately available:
    #
    # New DeviceManager method:
    #   ${result}=    Dm New Query Method    arg1
    #
    # New BoardfarmConfig method:
    #   ${setting}=    Config Get New Setting
    #
    # New device method:
    #   ${result}=    ACS.Nbi New Operation    arg1    arg2
    #
    # No code changes to robotframework-boardfarm needed!

    Log    Dynamic discovery means automatic adaptation to Boardfarm updates

*** Keywords ***
Setup Test Environment
    [Documentation]    Common setup for all tests.
    Log    Test environment ready

Teardown Test Environment
    [Documentation]    Common teardown for all tests.
    Clear Test Context
