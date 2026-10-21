$ErrorActionPreference='Stop'
Add-Type @'
using System; using System.Runtime.InteropServices;
public class OfficeRot { [DllImport("oleaut32.dll", PreserveSig=false)] public static extern void GetActiveObject(ref Guid clsid, IntPtr reserved, [MarshalAs(UnmanagedType.IUnknown)] out object obj); }
'@
$work='D:\project\autotest\downloads\beili-document-work'
$target='C:\Users\26713\Desktop\beili.doc'
$model=Get-Content -LiteralPath "$work\table-data.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$g=[Guid]'000209FF-0000-0000-C000-000000000046';$app=$null
[OfficeRot]::GetActiveObject([ref]$g,[IntPtr]::Zero,[ref]$app)
$doc=$null
for($i=1;$i -le $app.Documents.Count;$i++){if($app.Documents.Item($i).FullName -eq $target){$doc=$app.Documents.Item($i);break}}
if($null -eq $doc){throw 'Requested document is not open'}
if($doc.ReadOnly){throw 'Document is read-only'}
if($doc.Tables.Count -ne 1 -or $doc.Tables.Item(1).Rows.Count -ne 3){throw 'Unexpected table structure; no changes made'}
$table=$doc.Tables.Item(1)
if($table.Cell(3,1).Range.Text.Trim([char]13,[char]7).Length -ne 0){throw 'Table already contains data'}
$beforeImages=$doc.InlineShapes.Count
$beforeText=$doc.Content.Text
[IO.File]::WriteAllText("$work\before-flat.xml",$doc.WordOpenXML,[Text.UTF8Encoding]::new($false))
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$backup="C:\Users\26713\Desktop\beili.before-$stamp.doc"
$doc.Save()
$src=[IO.File]::Open($target,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
try{$dst=[IO.File]::Create($backup);try{$src.CopyTo($dst)}finally{$dst.Dispose()}}finally{$src.Dispose()}
$oldUpdate=$app.ScreenUpdating
$app.ScreenUpdating=$false
try {
  $after=$doc.Range($table.Range.End,$table.Range.End)
  $after.InsertBreak(2)
  $table.Range.InsertParagraphBefore()
  $before=$doc.Range($table.Range.Start-1,$table.Range.Start-1)
  $before.InsertBreak(2)
  $section=$table.Range.Sections.Item(1)
  $section.PageSetup.Orientation=1
  $section.PageSetup.PageWidth=841.9
  $section.PageSetup.PageHeight=595.3
  $section.PageSetup.LeftMargin=36
  $section.PageSetup.RightMargin=36
  $section.PageSetup.TopMargin=32
  $section.PageSetup.BottomMargin=32
  $table.Range.InsertParagraphBefore()
  $intro=$doc.Range($table.Range.Start-1,$table.Range.Start-1)
  $intro.Text="普通文本空格校验异常结果`r纯空格输入为3个空格；首尾输入各含2个空格，应过滤两端空格，中间空格保留。特殊类型、枚举及自动生成字段不在范围内。`r共26项功能，纯空格23项未通过、3项通过，首尾空格26项未通过。下表为原始断言JSON；更新日志content补充存储回读断言。`r纯空格通过仅表示组合请求被拒绝，不代表每个字段均已独立校验。执行记录号可在autotest核对。`r"
  $intro.Font.NameFarEast='宋体'
  $intro.Font.Size=10
  $intro.ParagraphFormat.SpaceAfter=4
  $intro.ParagraphFormat.KeepWithNext=$true
  $groups=@($model.rows | Group-Object source_id)
  for($i=1;$i -lt $groups.Count;$i++){$null=$table.Rows.Add()}
  $table.AllowAutoFit=$false
  $table.AutoFitBehavior(0)
  $table.PreferredWidthType=3
  $table.PreferredWidth=769.9
  $widths=@(83.0,94.0,247.0,49.0,247.0,49.9)
  for($r=3;$r -le $table.Rows.Count;$r++){
    for($c=1;$c -le 6;$c++){$table.Cell($r,$c).SetWidth($widths[$c-1],0)}
  }
  $table.Cell(1,1).SetWidth(83,0)
  $table.Cell(1,2).SetWidth(94,0)
  $table.Cell(1,3).SetWidth(296,0)
  $table.Cell(1,4).SetWidth(296.9,0)
  for($c=3;$c -le 6;$c++){$table.Cell(2,$c).SetWidth($widths[$c-1],0)}
  $table.TopPadding=6
  $table.BottomPadding=6
  $table.LeftPadding=6
  $table.RightPadding=6
  $table.Range.Font.Name='Arial'
  $table.Range.Font.NameFarEast='宋体'
  $table.Range.Font.Size=10
  $table.Range.ParagraphFormat.SpaceBefore=0
  $table.Range.ParagraphFormat.SpaceAfter=0
  $table.Range.ParagraphFormat.KeepWithNext=$false
  $table.Range.ParagraphFormat.KeepTogether=$false
  $table.Rows.AllowBreakAcrossPages=$false
  $table.Rows.HeadingFormat=$false
  $table.Rows.Item(1).HeadingFormat=$true
  $table.Rows.Item(2).HeadingFormat=$true
  foreach($cell in $table.Range.Cells){$cell.VerticalAlignment=0}
  $labels=@{name='名称';description='描述或备注';note='备注';title='标题';notes='备注';address='地址';bank_name='银行名称';version='版本';content='内容';account_name='账户名称';bank_branch='支行';purpose='用途';reason='原因';deliverables='交付内容'}
  for($i=0;$i -lt $groups.Count;$i++){
    $row=$i+3
    $s=$groups[$i].Group | Where-Object variant -eq 'spaces'
    $t=$groups[$i].Group | Where-Object variant -eq 'trim'
    $fieldText=($s.fields | ForEach-Object {"$_`r$($labels[$_])"}) -join "`r`r"
    $table.Cell($row,1).Range.Text=$s.feature
    $table.Cell($row,2).Range.Text=$fieldText
    foreach($item in @(@{result=$s;jsoncol=3;statuscol=4},@{result=$t;jsoncol=5;statuscol=6})){
      $v=$item.result
      $json=ConvertTo-Json -InputObject @($v.assertions) -Depth 12
      $text="执行记录 #$($v.record_id)`r"+$json.Replace("`r`n","`n").Replace("`n",[string][char]11)
      if($v.variant -eq 'trim' -and $v.source_id -in @(20610,20614)){
        $extra=@($v.storage_assertion_details | Where-Object path -eq 'content')
        $storage=ConvertTo-Json -InputObject $extra -Depth 8
        $text+="`rcontent 存储回读`r"+$storage.Replace("`r`n","`n").Replace("`n",[string][char]11)
      }
      $cell=$table.Cell($row,$item.jsoncol)
      $cell.Range.Text=$text
      $cell.Range.Font.Name='Consolas'
      $cell.Range.Font.NameFarEast='宋体'
      $cell.Range.Font.Size=9
      $cell.Range.ParagraphFormat.LineSpacingRule=0
      $cell.Range.ParagraphFormat.Alignment=0
      $status=$table.Cell($row,$item.statuscol)
      $status.Range.Text=$(if($v.final_status -eq 'passed'){'通过'}else{'未通过'})
      $status.Range.ParagraphFormat.Alignment=1
      $status.Range.Font.Color=$(if($v.final_status -eq 'passed'){32768}else{192})
      $status.VerticalAlignment=1
    }
  }
  $doc.Repaginate()
  $doc.Save()
  [IO.File]::WriteAllText("$work\after-flat.xml",$doc.WordOpenXML,[Text.UTF8Encoding]::new($false))
  $doc.ExportAsFixedFormat("$work\beili-updated.pdf",17)
  @{target=$target;backup=$backup;rows=$table.Rows.Count;images_before=$beforeImages;images_after=$doc.InlineShapes.Count;pages=$doc.ComputeStatistics(2);sections=$doc.Sections.Count;saved=$doc.Saved;widths=@(1..6 | ForEach-Object {$table.Cell(3,$_).Width})} | ConvertTo-Json -Depth 5
} finally {$app.ScreenUpdating=$oldUpdate}
