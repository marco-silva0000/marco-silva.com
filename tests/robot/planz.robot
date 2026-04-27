*** Settings ***
Library    RequestsLibrary
Library    Collections

Suite Setup    Create Session    app    http://localhost:8000

*** Variables ***
${PASSWORD}    planz
${WRONG_PASS}    wrongpassword

*** Test Cases ***
Planz Page Returns 200
    ${resp}=    GET On Session    app    /tools/planz/
    Should Be Equal As Integers    ${resp.status_code}    200

Planz Page Contains Password Form
    ${resp}=    GET On Session    app    /tools/planz/
    Should Contain    ${resp.text}    password

Wrong Password Returns Error
    ${resp}=    POST On Session    app    /tools/planz/auth/    data=passwd=${WRONG_PASS}
    Should Contain    ${resp.text}    wrong password

Correct Password Via Query Param Shows Calendar
    ${resp}=    GET On Session    app    url=/tools/planz/?passwd=${PASSWORD}
    Should Be Equal As Integers    ${resp.status_code}    200
    Should Contain    ${resp.text}    planz-nav

Correct Password Via Auth Endpoint Shows Calendar
    ${resp}=    POST On Session    app    /tools/planz/auth/    data=passwd=${PASSWORD}
    Should Be Equal As Integers    ${resp.status_code}    200

Navigate Endpoint Requires Password
    ${resp}=    GET On Session    app    url=/tools/planz/nav/?passwd=${WRONG_PASS}
    Should Contain    ${resp.text}    enter password

Navigate Endpoint With Password Returns Calendar
    ${resp}=    GET On Session    app    url=/tools/planz/nav/?passwd=${PASSWORD}&days=3
    Should Be Equal As Integers    ${resp.status_code}    200
    Should Contain    ${resp.text}    planz-nav

Navigate With 1 Day View
    ${resp}=    GET On Session    app    url=/tools/planz/nav/?passwd=${PASSWORD}&days=1
    Should Contain    ${resp.text}    cols-1

Navigate With 3 Day View
    ${resp}=    GET On Session    app    url=/tools/planz/nav/?passwd=${PASSWORD}&days=3
    Should Contain    ${resp.text}    cols-3

Navigate With Week View
    ${resp}=    GET On Session    app    url=/tools/planz/nav/?passwd=${PASSWORD}&days=7
    Should Contain    ${resp.text}    cols-7

Navigate With Start Date
    ${resp}=    GET On Session    app    url=/tools/planz/nav/?passwd=${PASSWORD}&days=3&start=2026-04-28
    Should Be Equal As Integers    ${resp.status_code}    200
    Should Contain    ${resp.text}    28 Apr

ICS Download Endpoint Returns Calendar File
    ${resp}=    GET On Session    app    url=/tools/planz/event.ics?title=Test&start=2026-04-28T10:00
    Should Be Equal As Integers    ${resp.status_code}    200
    Should Contain    ${resp.text}    BEGIN:VCALENDAR
    Should Contain    ${resp.text}    Test

All View Buttons Present
    ${resp}=    GET On Session    app    url=/tools/planz/?passwd=${PASSWORD}
    Should Contain    ${resp.text}    1 day
    Should Contain    ${resp.text}    3 day
    Should Contain    ${resp.text}    week

Default View Is 3 Days
    ${resp}=    GET On Session    app    url=/tools/planz/?passwd=${PASSWORD}
    Should Contain    ${resp.text}    cols-3
