import Foundation

enum BridgeResponse {
    static func decode(_ bytes: Data, exit: Int32) -> [String:Any] {
        if let object=try? JSONSerialization.jsonObject(with:bytes) as? [String:Any] {return object}
        let text=String(data:bytes,encoding:.utf8) ?? ""
        for line in text.split(separator:"\n").reversed() {
            if let object=try? JSONSerialization.jsonObject(with:Data(line.utf8)) as? [String:Any] {return object}
        }
        return ["error":"Cannot read run data (exit "+String(exit)+"). "+String(text.prefix(280))]
    }
}
