// Makes the site's images in src/assets/generated from the app's screenshots and icon:
// screenshots as JPEG at 1600 and 800 px on the page colour, icons at 32, 180 and 512 px, and the
// 1200x630 card that link previews show. Run: swift src/make-assets.swift <screenshots folder>
import AppKit
import ImageIO
import UniformTypeIdentifiers

let page = NSColor(srgbRed: 0x11 / 255.0, green: 0x1B / 255.0, blue: 0x20 / 255.0, alpha: 1)
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

// Link preview card: icon, name and line on the page colour.
let card = render(width: 1200, height: 630, background: page) { ctx in
    ctx.draw(icon, in: CGRect(x: 110, y: 175, width: 280, height: 280))
    NSGraphicsContext.current = NSGraphicsContext(cgContext: ctx, flipped: false)
    func font(_ size: CGFloat, _ weight: NSFont.Weight, serif: Bool) -> NSFont {
        let base = NSFont.systemFont(ofSize: size, weight: weight)
        return serif ? NSFont(descriptor: base.fontDescriptor.withDesign(.serif)!, size: size)! : base
    }
    NSAttributedString(string: "Harbor", attributes: [.font: font(108, .medium, serif: true), .foregroundColor: NSColor.white]).draw(at: CGPoint(x: 450, y: 330))
    NSAttributedString(string: "Windows games on your Mac.", attributes: [.font: font(44, .regular, serif: false), .foregroundColor: NSColor(srgbRed: 0.93, green: 0.59, blue: 0.35, alpha: 1)]).draw(at: CGPoint(x: 454, y: 262))
    NSAttributedString(string: "Free for Apple silicon · harbormac.github.io", attributes: [.font: font(28, .regular, serif: false), .foregroundColor: NSColor(srgbRed: 0.57, green: 0.66, blue: 0.68, alpha: 1)]).draw(at: CGPoint(x: 456, y: 205))
}
write(card, "og-image.png", jpeg: false)
