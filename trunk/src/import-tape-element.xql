xquery version "1.0";
 
declare namespace import-tape-element = "http://www.ishafoundation.org/ts4isha/xquery/import-tape-element";

declare variable $import-tape-element:collectionPath := '/db/lto4isha/data';
declare variable $import-tape-element:idPrefix := 'tape-';

declare option exist:serialize "media-type=text/plain";

declare function import-tape-element:get-next-tape-id() as xs:string
{
	let $maxId := (max(collection($import-tape-element:collectionPath)//tape/import-tape-element:get-id-component(@id)), 0)[1]
	return
		concat($import-tape-element:idPrefix, $maxId + 1)
};

declare function import-tape-element:get-id-component($id as xs:string?) as xs:integer?
{
	if (empty($id)) then
		()
	else
		let $onlyDigits := replace($id, '\D', '')
		return
			if ($onlyDigits = '') then
				()
			else
				xs:integer($onlyDigits)
};

declare function import-tape-element:add-or-update-attributes($elements as element()*, $attrNames as xs:QName*, $attrValues as xs:anyAtomicType*) as element()?
{
	for $element in $elements
	return element
		{node-name($element)}
		{
		for $attrName at $seq in $attrNames
		return attribute {$attrName}
		                 {$attrValues[$seq]},
			$element/@*[not(node-name(.) = $attrNames)],
			$element/node()
		}
};

declare function import-tape-element:create-collection($path as xs:string) as empty()
{
	let $null := import-tape-element:create-collection-internal('/', tokenize($path, '/'))
	return ()
};

declare function import-tape-element:create-collection-internal($baseCollection as xs:string, $seq as xs:string*) as xs:string
{
	if (empty($seq)) then
		$baseCollection
	else
		let $newBaseCollection :=
			if ($seq[1] = '') then
				$baseCollection
			else
				xmldb:create-collection($baseCollection, $seq[1])
		let $newSeq := $seq[position() > 1]
		return import-tape-element:create-collection-internal($newBaseCollection, $newSeq)
};

if (not(xmldb:is-admin-user(xmldb:get-current-user()))) then	
	error((xs:QName('access-control-exception')), 'Only admin user allowed to call this script')
else

let $null := import-tape-element:create-collection($import-tape-element:collectionPath)

let $tapeXML := util:parse(request:get-parameter('tapeXML', ()))
return
	if (empty($tapeXML)) then
		error(xs:QName('missing-argument-exception'), 'No tapeXML specified')
	else
		let $newId := import-tape-element:get-next-tape-id()
		let $tapeXML := import-tape-element:add-or-update-attributes($tapeXML, xs:QName('id'), $newId)
		let $filename := concat($newId, '.xml')
		let $null := xmldb:store($import-tape-element:collectionPath, $filename, $tapeXML)
		return
			$newId
