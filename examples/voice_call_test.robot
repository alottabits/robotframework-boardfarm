*** Settings ***
Documentation    Example voice/SIP call test using UseCaseLibrary.
...
...    This suite demonstrates voice testing with Boardfarm use_cases.
...    The voice use_cases provide a high-level abstraction for SIP phone
...    operations that work across different SIP phone implementations.

Library    BoardfarmLibrary
Library    UseCaseLibrary

Suite Setup       Setup Voice Test Environment
Suite Teardown    Teardown Voice Test Environment


*** Variables ***
${PHONE1}    ${EMPTY}
${PHONE2}    ${EMPTY}


*** Test Cases ***
Test Basic Voice Call
    [Documentation]    Test basic voice call establishment and teardown.
    ...
    ...    Uses: voice.call_a_phone(), voice.answer_a_call(),
    ...          voice.is_call_ringing(), voice.is_call_connected(),
    ...          voice.disconnect_the_call()
    [Tags]    use_case:voice    call

    # Phone 1 calls Phone 2
    Voice Call A Phone    ${PHONE1}    ${PHONE2}

    # Phone 2 should be ringing
    ${ringing}=    Voice Is Call Ringing    ${PHONE2}
    Should Be True    ${ringing}    Phone 2 should be ringing

    # Phone 2 answers
    Voice Answer A Call    ${PHONE2}

    # Both phones should be connected
    ${connected1}=    Voice Is Call Connected    ${PHONE1}
    ${connected2}=    Voice Is Call Connected    ${PHONE2}
    Should Be True    ${connected1}    Phone 1 should be connected
    Should Be True    ${connected2}    Phone 2 should be connected

    # Phone 1 hangs up
    Voice Disconnect The Call    ${PHONE1}

    # Verify call ended
    Log    Call completed successfully


Test Call On Hold
    [Documentation]    Test call hold and resume functionality.
    ...
    ...    Uses: voice.place_call_onhold(), voice.is_call_on_hold()
    [Tags]    use_case:voice    hold

    # Establish call
    Voice Call A Phone    ${PHONE1}    ${PHONE2}
    Voice Answer A Call    ${PHONE2}

    # Place call on hold
    Voice Place Call Onhold    ${PHONE1}

    # Verify hold status
    ${on_hold}=    Voice Is Call On Hold    ${PHONE1}
    Should Be True    ${on_hold}    Call should be on hold

    # Take call off hold
    Voice Place Call Offhold    ${PHONE1}

    # Verify call reconnected
    ${connected}=    Voice Is Call Connected    ${PHONE1}
    Should Be True    ${connected}    Call should be reconnected

    # Cleanup
    Voice Disconnect The Call    ${PHONE1}


*** Keywords ***
Setup Voice Test Environment
    [Documentation]    Initialize SIP phones for testing.
    ${phone1}=    Get Device By Type    SIPPhone    index=0
    ${phone2}=    Get Device By Type    SIPPhone    index=1

    Set Suite Variable    ${PHONE1}    ${phone1}
    Set Suite Variable    ${PHONE2}    ${phone2}

    # Initialize phones using use_cases
    Voice Initialize Phone    ${PHONE1}
    Voice Initialize Phone    ${PHONE2}

    Log    Voice test environment initialized

Teardown Voice Test Environment
    [Documentation]    Cleanup SIP phones after testing.
    # Shutdown phones using use_cases
    Run Keyword And Ignore Error    Voice Shutdown Phone    ${PHONE1}
    Run Keyword And Ignore Error    Voice Shutdown Phone    ${PHONE2}

    Log    Voice test environment cleaned up
