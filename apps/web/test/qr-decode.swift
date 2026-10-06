// macOS-only test utility; Vision is provided by the operating system.
import Foundation
import Vision
let request = VNDetectBarcodesRequest()
request.symbologies = [.qr]
try VNImageRequestHandler(url: URL(fileURLWithPath: CommandLine.arguments[1])).perform([request])
guard let payload = request.results?.first?.payloadStringValue else { exit(1) }
print(payload)
