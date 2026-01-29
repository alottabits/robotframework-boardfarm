*** Settings ***
Documentation    Example networking test suite using UseCaseLibrary.
...
...    This suite demonstrates network testing with Boardfarm use_cases.
...    The networking use_cases provide high-level abstractions for
...    common network operations like ping, DNS, HTTP, etc.

Library    BoardfarmLibrary
Library    UseCaseLibrary


*** Test Cases ***
Test LAN Connectivity Via Ping
    [Documentation]    Verify LAN client can ping external hosts.
    ...
    ...    Uses: networking.ping()
    [Tags]    use_case:networking    ping

    ${lan}=    Get Device By Type    LAN

    # Ping external DNS server
    ${result}=    Networking Ping    ${lan}    8.8.8.8    ping_count=4
    Should Be True    ${result}    Ping to 8.8.8.8 should succeed


Test DNS Resolution
    [Documentation]    Verify DNS resolution is working.
    ...
    ...    Uses: networking.dns_lookup()
    [Tags]    use_case:networking    dns

    ${lan}=    Get Device By Type    LAN

    # Resolve Google domain
    ${dns_result}=    Networking Dns Lookup    ${lan}    google.com
    Log    DNS result: ${dns_result}
    Should Not Be Empty    ${dns_result}    DNS lookup should return result


Test HTTP Access
    [Documentation]    Verify HTTP access works through the network.
    ...
    ...    Uses: networking.http_get()
    [Tags]    use_case:networking    http

    ${lan}=    Get Device By Type    LAN

    # HTTP GET request
    ${http_result}=    Networking Http Get    ${lan}    http://example.com
    Log    HTTP response received
    Should Not Be Empty    ${http_result}    HTTP response should not be empty


Test TCP Session Creation
    [Documentation]    Test TCP session establishment.
    ...
    ...    Uses: networking.create_tcp_session()
    [Tags]    use_case:networking    tcp

    ${lan}=    Get Device By Type    LAN
    ${wan}=    Get Device By Type    WAN

    # Create TCP session between LAN and WAN
    ${session}=    Networking Create Tcp Session    ${lan}    ${wan}
    ...    ip_type=ipv4    port=8080
    Log    TCP session: ${session}
