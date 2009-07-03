xquery version "1.0";

import module namespace utils = "http://www.ishafoundation.org/ts4isha/xquery/utils" at "utils.xqm";

let $sessionId := request:get-parameter("sessionId", ())
let $sessionXML := utils:get-session($sessionId)
let $eventId := $sessionXML/@eventId
let $eventXML := utils:get-event($eventId)
return
	utils:build-session-full-name($sessionXML, $eventXML)