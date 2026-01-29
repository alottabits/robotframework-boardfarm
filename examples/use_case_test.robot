*** Settings ***
Documentation    Example test suite demonstrating UseCaseLibrary keywords.
...
...    This suite shows the RECOMMENDED approach for writing Robot Framework
...    tests with Boardfarm: using UseCaseLibrary keywords that map directly
...    to boardfarm3.use_cases functions.
...
...    Benefits of this approach:
...    - Single source of truth: Same use_cases used by pytest-bdd
...    - Portability: Tests can be easily migrated between frameworks
...    - Maintainability: Fix once in use_cases, benefit everywhere
...    - Documentation: Use cases document which test statements they implement

Library    BoardfarmLibrary
Library    UseCaseLibrary

Suite Setup       Log    Starting Boardfarm use_case tests
Suite Teardown    Log    Completed Boardfarm use_case tests


*** Test Cases ***
Test CPE Performance Metrics
    [Documentation]    Verify CPE performance using use_case keywords.
    ...
    ...    Uses: cpe.get_cpu_usage(), cpe.get_memory_usage(), cpe.get_seconds_uptime()
    [Tags]    use_case:cpe    performance

    ${cpe}=    Get Device By Type    CPE

    # Get CPU usage via use_case
    ${cpu}=    Cpe Get Cpu Usage    ${cpe}
    Log    CPU Usage: ${cpu}%
    Should Be True    ${cpu} < 90    CPU usage too high: ${cpu}%

    # Get memory usage via use_case
    ${memory}=    Cpe Get Memory Usage    ${cpe}
    Log    Memory: ${memory}

    # Get uptime via use_case
    ${uptime}=    Cpe Get Seconds Uptime    ${cpe}
    Log    Uptime: ${uptime} seconds
    Should Be True    ${uptime} > 0    Uptime should be positive


Test ACS Parameter Operations
    [Documentation]    Test TR-069 parameter operations via ACS use_cases.
    ...
    ...    Uses: acs.get_parameter_value(), acs.is_cpe_online()
    [Tags]    use_case:acs    tr069

    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE

    # Check if CPE is online via use_case
    ${online}=    Acs Is Cpe Online    ${acs}    ${cpe}
    Should Be True    ${online}    CPE should be online

    # Get firmware version via use_case
    ${version}=    Acs Get Parameter Value    ${acs}    ${cpe}
    ...    Device.DeviceInfo.SoftwareVersion
    Log    Firmware Version: ${version}
    Should Not Be Empty    ${version}    Firmware version should not be empty


Test ACS Parameter With Interface Selection
    [Documentation]    Demonstrate interface selection using 'via' parameter.
    ...
    ...    The 'via' parameter allows choosing between NBI (API) and GUI interfaces.
    ...    Default is "nbi" which is faster for automation.
    [Tags]    use_case:acs    interface_selection

    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE

    # Get parameter via NBI (default)
    ${value_nbi}=    Acs Get Parameter Value    ${acs}    ${cpe}
    ...    Device.DeviceInfo.Manufacturer
    Log    Manufacturer (via NBI): ${value_nbi}

    # Explicit NBI selection
    ${value_explicit}=    Acs Get Parameter Value    ${acs}    ${cpe}
    ...    Device.DeviceInfo.Manufacturer    via=nbi
    Should Be Equal    ${value_nbi}    ${value_explicit}


Test NTP Synchronization Status
    [Documentation]    Check NTP synchronization status via use_case.
    ...
    ...    Uses: cpe.is_ntp_synchronized()
    [Tags]    use_case:cpe    ntp

    ${cpe}=    Get Device By Type    CPE

    ${synced}=    Cpe Is Ntp Synchronized    ${cpe}
    Log    NTP Synchronized: ${synced}
    # Note: NTP might not be synchronized in all environments


Test TR-069 Agent Status
    [Documentation]    Verify TR-069 agent is running via use_case.
    ...
    ...    Uses: cpe.is_tr069_agent_running()
    [Tags]    use_case:cpe    tr069

    ${cpe}=    Get Device By Type    CPE

    ${running}=    Cpe Is Tr069 Agent Running    ${cpe}
    Log    TR-069 Agent Running: ${running}
    Should Be True    ${running}    TR-069 agent should be running


Test CPE Provisioning Mode
    [Documentation]    Get CPE provisioning mode via use_case.
    ...
    ...    Uses: cpe.get_cpe_provisioning_mode()
    [Tags]    use_case:cpe    provisioning

    ${cpe}=    Get Device By Type    CPE

    ${mode}=    Cpe Get Cpe Provisioning Mode    ${cpe}
    Log    Provisioning Mode: ${mode}
    Should Match Regexp    ${mode}    ^(dual|ipv4|ipv6|bridge)$


*** Keywords ***
Log Test Context
    [Documentation]    Helper keyword to log test context information.
    [Arguments]    ${key}    ${value}
    Set Test Context    ${key}    ${value}
    Log    Context: ${key} = ${value}
