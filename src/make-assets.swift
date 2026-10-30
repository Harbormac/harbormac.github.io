// Makes the site's images in src/assets/generated from the app's screenshots and icon:
// screenshots as JPEG at 1600 and 800 px on the page colour, icons at 32, 180 and 512 px, and the
// 1200x630 cards that link previews show (one for the site, one per guide). Run: swift src/make-assets.swift <screenshots folder>
import AppKit
import ImageIO
import UniformTypeIdentifiers

let page = NSColor(srgbRed: 0x0B / 255.0, green: 0x10 / 255.0, blue: 0x26 / 255.0, alpha: 1)
let root = URL(fileURLWithPath: CommandLine.arguments[0]).deletingLastPathComponent()
let out = root.appendingPathComponent("assets/generated")
try? FileManager.default.createDirectory(at: out, withIntermediateDirectories: true)
let shots = URL(fileURLWithPath: CommandLine.arguments[1])

func load(_ url: URL) -> CGImage { CGImageSourceCreateImageAtIndex(CGImageSourceCreateWithURL(url as CFURL, nil)!, 0, nil)! }
func write(_ image: CGImage, _ name: String, jpeg: Bool) {
    let dest = CGImageDestinationCreateWithURL(out.appendingPathComponent(name) as CFURL, (jpeg ? UTType.jpeg : UTType.png).identifier as CFString, 1, nil)!
    CGImageDestinationAddImage(dest, image, jpeg ? [kCGImageDestinationLossyCompressionQuality: 0.82] as CFDictionary : nil)
    CGImageDestinationFinalize(dest)
}
func render(width: Int, height: Int, background: NSColor?, _ draw: (CGContext) -> Void) -> CGImage {
    let ctx = CGContext(data: nil, width: width, height: height, bitsPerComponent: 8, bytesPerRow: 0, space: CGColorSpace(name: CGColorSpace.sRGB)!,
                        bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
    ctx.interpolationQuality = .high
    if let background { ctx.setFillColor(background.cgColor); ctx.fill(CGRect(x: 0, y: 0, width: width, height: height)) }
    draw(ctx)
    return ctx.makeImage()!
}

for name in ["library", "bottles", "game-settings", "snapshots", "component-updates"] {
    let image = load(shots.appendingPathComponent("\(name).png"))
    for width in [1600, 800] {
        let height = Int((Double(image.height) * Double(width) / Double(image.width)).rounded())
        write(render(width: width, height: height, background: page) { $0.draw(image, in: CGRect(x: 0, y: 0, width: width, height: height)) }, "\(name)-\(width).jpg", jpeg: true)
    }
}

let icon = load(root.appendingPathComponent("assets/icon-512.png"))
for size in [32, 180, 512] {
    write(render(width: size, height: size, background: size == 180 ? page : nil) { $0.draw(icon, in: CGRect(x: 0, y: 0, width: size, height: size)) }, "icon-\(size).png", jpeg: false)
}

func font(_ size: CGFloat, _ weight: NSFont.Weight, display: Bool) -> NSFont {
    let base = NSFont.systemFont(ofSize: size, weight: weight)
    return display ? NSFont(descriptor: base.fontDescriptor.withDesign(.rounded)!, size: size)! : base
}
let accent = NSColor(srgbRed: 1.0, green: 0.541, blue: 0.239, alpha: 1)
let muted = NSColor(srgbRed: 0.604, green: 0.639, blue: 0.780, alpha: 1)

// Link preview card: icon, name and line on the page colour.
let card = render(width: 1200, height: 630, background: page) { ctx in
    ctx.draw(icon, in: CGRect(x: 110, y: 175, width: 280, height: 280))
    NSGraphicsContext.current = NSGraphicsContext(cgContext: ctx, flipped: false)
    NSAttributedString(string: "Portnaut", attributes: [.font: font(108, .bold, display: true), .foregroundColor: NSColor.white]).draw(at: CGPoint(x: 450, y: 330))
    NSAttributedString(string: "Windows games on your Mac.", attributes: [.font: font(44, .regular, display: false), .foregroundColor: accent]).draw(at: CGPoint(x: 454, y: 262))
    NSAttributedString(string: "Free for Apple silicon · portnaut.com", attributes: [.font: font(28, .regular, display: false), .foregroundColor: muted]).draw(at: CGPoint(x: 456, y: 205))
}
write(card, "og-image.png", jpeg: false)

// A card per guide: its title beside the screenshot that fits it best.
let guides = [("steam-on-mac", "Steam games on a Mac", "game-settings"),
              ("ubisoft-connect-on-mac", "Ubisoft Connect games on a Mac", "library"),
              ("ea-app-on-mac", "The EA app on a Mac", "component-updates"),
              ("dxmt-vs-d3dmetal-vs-dxvk", "DXMT, D3DMetal or DXVK?", "bottles"),
              ("open-exe-files-on-mac", "Open .exe files on a Mac", "library"),
              ("windows-emulator-for-mac", "Windows emulator for Mac?", "game-settings"),
              ("game-porting-toolkit", "Game Porting Toolkit, without Terminal", "component-updates"),
              ("install-wine-on-mac", "Install Wine on a Mac, without Homebrew", "bottles"),
              ("troubleshooting", "Troubleshooting Windows games on a Mac", "snapshots")]
for (slug, title, shot) in guides {
    let image = load(shots.appendingPathComponent("\(shot).png"))
    let guideCard = render(width: 1200, height: 630, background: page) { ctx in
        let frame = CGRect(x: 620, y: 105, width: 540, height: 540 * CGFloat(image.height) / CGFloat(image.width))
        ctx.saveGState()
        ctx.addPath(CGPath(roundedRect: frame, cornerWidth: 14, cornerHeight: 14, transform: nil))
        ctx.clip()
        ctx.draw(image, in: frame)
        ctx.restoreGState()
        ctx.draw(icon, in: CGRect(x: 72, y: 486, width: 64, height: 64))
        NSGraphicsContext.current = NSGraphicsContext(cgContext: ctx, flipped: false)
        NSAttributedString(string: "Portnaut guide", attributes: [.font: font(30, .semibold, display: false), .foregroundColor: accent]).draw(at: CGPoint(x: 152, y: 498))
        NSAttributedString(string: title, attributes: [.font: font(62, .bold, display: true), .foregroundColor: NSColor.white]).draw(with: CGRect(x: 72, y: 190, width: 510, height: 250), options: [.usesLineFragmentOrigin])
        NSAttributedString(string: "Free for Apple silicon · portnaut.com", attributes: [.font: font(24, .regular, display: false), .foregroundColor: muted]).draw(at: CGPoint(x: 74, y: 80))
    }
    write(guideCard, "og-\(slug).jpg", jpeg: true)
}
