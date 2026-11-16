# Offline fallback for PCs without Pillow: derive runtime plates from approved PNGs.
Add-Type -AssemblyName System.Drawing
$gamePath = Split-Path $PSScriptRoot -Parent
$assetPath = Join-Path $gamePath 'assets'
$yardSource = [Drawing.Bitmap]::new((Join-Path $assetPath 'yard.png'))
$yard = [Drawing.Bitmap]::new($yardSource)
for ($px=279; $px -lt 296; $px++) {
    for ($py=152; $py -lt 195; $py++) {
        $yard.SetPixel($px,$py,$yardSource.GetPixel($px,140))
    }
}
for ($px=389; $px -lt 434; $px++) {
    for ($py=259; $py -lt 274; $py++) {
        $yard.SetPixel($px,$py,$yardSource.GetPixel(350,$py))
    }
}
$yard.Save((Join-Path $assetPath 'yard-open.png'),[Drawing.Imaging.ImageFormat]::Png)
$yard.Dispose(); $yardSource.Dispose()
$icon = [Drawing.Bitmap]::new(128,128)
$graphics = [Drawing.Graphics]::FromImage($icon)
$graphics.InterpolationMode = [Drawing.Drawing2D.InterpolationMode]::NearestNeighbor
foreach ($layer in @(@('title-bg.png',0,0,128,128),@('core.png',24,13,80,80))) {
    $picture = [Drawing.Bitmap]::new((Join-Path $assetPath $layer[0]))
    $graphics.DrawImage($picture,[Drawing.Rectangle]::new($layer[1],$layer[2],$layer[3],$layer[4]))
    $picture.Dispose()
}
$picture = [Drawing.Bitmap]::new((Join-Path $assetPath 'towers.png'))
$graphics.DrawImage($picture,[Drawing.Rectangle]::new(8,75,48,48),[Drawing.Rectangle]::new(48,0,24,24),[Drawing.GraphicsUnit]::Pixel)
$picture.Dispose()
$picture = [Drawing.Bitmap]::new((Join-Path $assetPath 'players.png'))
$graphics.DrawImage($picture,[Drawing.Rectangle]::new(76,75,48,48),[Drawing.Rectangle]::new(0,0,24,24),[Drawing.GraphicsUnit]::Pixel)
$picture.Dispose(); $graphics.Dispose()
$icon.Save((Join-Path $gamePath 'icon.png'),[Drawing.Imaging.ImageFormat]::Png)
$icon.Dispose()
# Reuse exact silhouettes for all reservation previews and numbered team markers.
$sheet = [Drawing.Bitmap]::new((Join-Path $assetPath 'towers.png'))
$ghosts = [Drawing.Bitmap]::new($sheet.Width,$sheet.Height)
for ($px=0; $px -lt $sheet.Width; $px++) {
    for ($py=0; $py -lt $sheet.Height; $py++) {
        $alpha = $sheet.GetPixel($px,$py).A
        if ($alpha -gt 0) { $ghosts.SetPixel($px,$py,[Drawing.Color]::FromArgb([int]($alpha/2),101,169,224)) }
    }
}
$ghosts.Save((Join-Path $assetPath 'reservations.png'),[Drawing.Imaging.ImageFormat]::Png)
$ghosts.Dispose(); $sheet.Dispose()
$pinSource = [Drawing.Bitmap]::new((Join-Path $assetPath 'pin-blue.png'))
$pins = [Drawing.Bitmap]::new(96,28)
$teamColors = @(@(64,185,167),@(101,169,224),@(220,153,88),@(223,113,145))
for ($i=0; $i -lt 4; $i++) {
    for ($px=0; $px -lt 24; $px++) {
        for ($py=0; $py -lt 28; $py++) {
            $color = $pinSource.GetPixel($px,$py)
            if ($color.R -eq 101 -and $color.G -eq 169 -and $color.B -eq 224) {
                $rgb = $teamColors[$i]
                $color = [Drawing.Color]::FromArgb($color.A,$rgb[0],$rgb[1],$rgb[2])
            }
            $pins.SetPixel($i*24+$px,$py,$color)
        }
    }
}
$pins.Save((Join-Path $assetPath 'pins.png'),[Drawing.Imaging.ImageFormat]::Png)
$pins.Dispose(); $pinSource.Dispose()
