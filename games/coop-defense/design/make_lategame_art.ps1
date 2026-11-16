# Offline atlas: one copy for a glow, jam crackle, drone + shadow, or pip row.
Add-Type -AssemblyName System.Drawing
$assetPath = Join-Path (Split-Path $PSScriptRoot -Parent) 'assets'
$atlas = [Drawing.Bitmap]::new(336,112)
$penColors = @('#40b9a7','#65a9e0','#dc9958','#df7191')
$graphics = [Drawing.Graphics]::FromImage($atlas)
for ($slot=0; $slot -lt 4; $slot++) {
    for ($frame=0; $frame -lt 2; $frame++) {
        $rgb = [Drawing.ColorTranslator]::FromHtml($penColors[$slot])
        $pen = [Drawing.Pen]::new([Drawing.Color]::FromArgb((150+105*$frame),$rgb),2)
        $graphics.DrawEllipse($pen,$slot*56+3,48*$frame+3,49,41)
        $pen.Dispose()
    }
}
for ($frame=0; $frame -lt 2; $frame++) {
    $offset = 224+56*$frame
    $pen = [Drawing.Pen]::new([Drawing.ColorTranslator]::FromHtml('#eb7650'),3)
    $graphics.DrawLines($pen,[Drawing.Point[]]@([Drawing.Point]::new($offset+3,11),[Drawing.Point]::new($offset+15,4),[Drawing.Point]::new($offset+10,20),[Drawing.Point]::new($offset+30,12),[Drawing.Point]::new($offset+42,27),[Drawing.Point]::new($offset+51,19)))
    $graphics.DrawLines($pen,[Drawing.Point[]]@([Drawing.Point]::new($offset+7,34),[Drawing.Point]::new($offset+19,27),[Drawing.Point]::new($offset+31,40),[Drawing.Point]::new($offset+46,35)))
    $pen.Dispose()
}
$ink = [Drawing.SolidBrush]::new([Drawing.ColorTranslator]::FromHtml('#29343b'))
$red = [Drawing.SolidBrush]::new([Drawing.ColorTranslator]::FromHtml('#eb7650'))
$gold = [Drawing.SolidBrush]::new([Drawing.ColorTranslator]::FromHtml('#f4bf70'))
$white = [Drawing.SolidBrush]::new([Drawing.ColorTranslator]::FromHtml('#fff4d6'))
$shadow = [Drawing.SolidBrush]::new([Drawing.Color]::FromArgb(100,41,52,59))
$graphics.FillEllipse($shadow,228,79,24,7)
$graphics.FillPolygon($ink,[Drawing.Point[]]@([Drawing.Point]::new(225,51),[Drawing.Point]::new(235,55),[Drawing.Point]::new(240,49),[Drawing.Point]::new(245,55),[Drawing.Point]::new(254,51),[Drawing.Point]::new(249,67),[Drawing.Point]::new(240,72),[Drawing.Point]::new(231,67)))
$graphics.FillRectangle($red,229,55,6,6); $graphics.FillRectangle($red,245,55,6,6)
$graphics.FillRectangle($gold,237,55,6,11); $graphics.FillRectangle($white,239,56,2,5)
$graphics.FillPolygon($white,[Drawing.Point[]]@([Drawing.Point]::new(266,48),[Drawing.Point]::new(260,57),[Drawing.Point]::new(265,57),[Drawing.Point]::new(262,64),[Drawing.Point]::new(272,53),[Drawing.Point]::new(267,53)))
for ($count=1; $count -le 5; $count++) {
    $graphics.FillRectangle($ink,40*($count-1),96,40,8)
    for ($pip=0; $pip -lt $count; $pip++) { $graphics.FillRectangle($gold,40*($count-1)+3+7*$pip,98,5,4) }
}
$graphics.Dispose()
$atlas.Save((Join-Path $assetPath 'lategame.png'),[Drawing.Imaging.ImageFormat]::Png)
$atlas.Dispose()
foreach ($brush in @($ink,$red,$gold,$white,$shadow)) { $brush.Dispose() }
$source = [Drawing.Bitmap]::new((Join-Path $assetPath 'effects.png'))
$bright = [Drawing.Bitmap]::new($source.Width,$source.Height)
$graphics = [Drawing.Graphics]::FromImage($bright)
$matrix = [Drawing.Imaging.ColorMatrix]::new()
$matrix.Matrix40=.22; $matrix.Matrix41=.22; $matrix.Matrix42=.22
$attributes = [Drawing.Imaging.ImageAttributes]::new(); $attributes.SetColorMatrix($matrix)
$graphics.DrawImage($source,[Drawing.Rectangle]::new(0,0,$source.Width,$source.Height),0,0,$source.Width,$source.Height,[Drawing.GraphicsUnit]::Pixel,$attributes)
$graphics.Dispose(); $attributes.Dispose(); $source.Dispose()
$bright.Save((Join-Path $assetPath 'effects-bright.png'),[Drawing.Imaging.ImageFormat]::Png)
$bright.Dispose()
$players = [Drawing.Bitmap]::new((Join-Path $assetPath 'players.png'))
$workers = [Drawing.Bitmap]::new(224,136)
$graphics = [Drawing.Graphics]::FromImage($workers)
$graphics.InterpolationMode = [Drawing.Drawing2D.InterpolationMode]::NearestNeighbor
$font = [Drawing.Font]::new('Arial',12,[Drawing.FontStyle]::Regular,[Drawing.GraphicsUnit]::Pixel)
$ink = [Drawing.SolidBrush]::new([Drawing.ColorTranslator]::FromHtml('#29343b'))
$late = [Drawing.Bitmap]::new((Join-Path $assetPath 'lategame.png'))
for ($slot=0; $slot -lt 4; $slot++) {
    $brush = [Drawing.SolidBrush]::new([Drawing.ColorTranslator]::FromHtml($penColors[$slot]))
    for ($boost=0; $boost -lt 2; $boost++) {
        $x=$slot*56; $y=$boost*68
        $graphics.DrawImage($players,[Drawing.Rectangle]::new($x,$y+17,48,48),[Drawing.Rectangle]::new($slot*24,0,24,24),[Drawing.GraphicsUnit]::Pixel)
        $graphics.FillRectangle($ink,$x+36,$y+21,18,20)
        $graphics.DrawString([string]($slot+1),$font,$brush,$x+39,$y+22)
        if ($boost) { $graphics.DrawImage($late,[Drawing.Rectangle]::new($x+18,$y,12,16),[Drawing.Rectangle]::new(260,48,12,16),[Drawing.GraphicsUnit]::Pixel) }
    }
    $brush.Dispose()
}
$graphics.Dispose(); $font.Dispose(); $ink.Dispose(); $late.Dispose(); $players.Dispose()
$workers.Save((Join-Path $assetPath 'workers.png'),[Drawing.Imaging.ImageFormat]::Png)
$workers.Dispose()
$towers = [Drawing.Bitmap]::new((Join-Path $assetPath 'towers.png'))
$late = [Drawing.Bitmap]::new((Join-Path $assetPath 'lategame.png'))
$mastery = [Drawing.Bitmap]::new(576,336)
$graphics = [Drawing.Graphics]::FromImage($mastery)
$graphics.InterpolationMode = [Drawing.Drawing2D.InterpolationMode]::NearestNeighbor
$gold = [Drawing.SolidBrush]::new([Drawing.ColorTranslator]::FromHtml('#f4bf70'))
for ($count=1; $count -le 6; $count++) {
    for ($index=0; $index -lt 12; $index++) {
        $x=$index*48; $y=($count-1)*56
        $graphics.DrawImage($towers,[Drawing.Rectangle]::new($x,$y,48,48),[Drawing.Rectangle]::new($index*24,0,24,24),[Drawing.GraphicsUnit]::Pixel)
        if ($count -le 5) {
            $graphics.DrawImage($late,[Drawing.Rectangle]::new($x+4,$y+47,40,8),[Drawing.Rectangle]::new(($count-1)*40,96,40,8),[Drawing.GraphicsUnit]::Pixel)
        } else {
            $graphics.FillPolygon($gold,[Drawing.Point[]]@([Drawing.Point]::new($x+17,$y+46),[Drawing.Point]::new($x+19,$y+49),[Drawing.Point]::new($x+23,$y+49),[Drawing.Point]::new($x+20,$y+52),[Drawing.Point]::new($x+21,$y+55),[Drawing.Point]::new($x+17,$y+53),[Drawing.Point]::new($x+13,$y+55),[Drawing.Point]::new($x+14,$y+52),[Drawing.Point]::new($x+11,$y+49),[Drawing.Point]::new($x+15,$y+49)))
        }
    }
}
$graphics.Dispose(); $gold.Dispose(); $towers.Dispose(); $late.Dispose()
$mastery.Save((Join-Path $assetPath 'mastery-towers.png'),[Drawing.Imaging.ImageFormat]::Png)
$mastery.Dispose()
# Exact integer HP widths + existing status silhouettes, one copy instead of two.
$enemies = [Drawing.Bitmap]::new((Join-Path $assetPath 'enemies.png'))
$effects = [Drawing.Bitmap]::new((Join-Path $assetPath 'effects.png'))
$health = [Drawing.Bitmap]::new(1980,588)
$graphics = [Drawing.Graphics]::FromImage($health)
$teal = [Drawing.SolidBrush]::new([Drawing.ColorTranslator]::FromHtml('#40b9a7'))
$sizes = @(22,28,44)
for ($kind=3; $kind -lt 6; $kind++) {
    $size=$sizes[$kind-3]
    for ($style=0; $style -lt 4; $style++) {
        for ($width=1; $width -le $size; $width++) {
            $x=$width*44; $y=(($kind-3)*4+$style)*49
            $source = if ($style -eq 0) { $enemies } else { $effects }
            $sourceY = if ($style -eq 0) { 0 } else { (20+$style)*128 }
            $graphics.DrawImage($source,[Drawing.Rectangle]::new($x,$y+5,$size,$size),[Drawing.Rectangle]::new($kind*44,$sourceY,$size,$size),[Drawing.GraphicsUnit]::Pixel)
            $graphics.FillRectangle($teal,$x,$y,$width,2)
        }
    }
}
$graphics.Dispose(); $teal.Dispose(); $enemies.Dispose(); $effects.Dispose()
$health.Save((Join-Path $assetPath 'enemy-health.png'),[Drawing.Imaging.ImageFormat]::Png)
$health.Dispose()
