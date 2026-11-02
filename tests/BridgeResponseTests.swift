import Foundation

@main struct BridgeResponseTests {
    static func main() {
        func decode(_ text:String,_ exit:Int32=0)->[String:Any] {BridgeResponse.decode(Data(text.utf8),exit:exit)}
        assert(decode("{\"title\":\"Run\"}")["title"] as? String == "Run")
        assert(decode("Python notice\n{\"title\":\"Run\"}\n")["title"] as? String == "Run")
        assert(decode("{\"title\":\"Run\"}\nRuntime notice\n")["title"] as? String == "Run")
        assert(decode("",15)["error"] as? String == "Cannot read run data (exit 15). ")
        assert((decode("invalid")["error"] as? String)?.contains("invalid") == true)
        print("5 bridge response assertions passed")
    }
}
