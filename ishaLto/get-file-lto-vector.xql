xquery version "1.0";
 
declare option exist:serialize "media-type=text/xml method=xml indent=yes";

let $collectionPath := '/db/lto4isha/data'
let $domain := request:get-parameter('domain', ())
let $ids := tokenize(request:get-parameter('ids', ()), '\s*,\s*')
return
	<vectors>{
		for $id in $ids
		let $media := collection($collectionPath)//*[local-name(.) eq $domain and @id=$id]
		let $tape_id := $media/../../@id
		let $tar_block := $media/../@block
	    let $record_offset := $media/@recordOffset
	    let $filename := $media/@filename
	    let $filesize := $media/@size
	    let $md5 := $media/@md5
	    order by $tape_id, $tar_block, $record_offset
	    return
	   		<vector domain="{$domain}" mediaId="{$id}" tapeId="{$tape_id}" tarBlock="{$tar_block}" recordOffset="{$record_offset}" filename="{$filename}" filesize="{$filesize}" md5="{$md5}"/>
	}</vectors>