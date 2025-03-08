#!/usr/bin/haserl
<%in p/common.cgi %>

<%
page_title="Camera runtime settings"

if [ "$REQUEST_METHOD" = "POST" ]; then
    case "$POST_action" in
        setfps)
            if echo "$POST_fps" | grep -qE '^[0-9]+$' && [ "$POST_fps" -ge 10 ] && [ "$POST_fps" -le 60 ]; then
                echo "setfps 0 $POST_fps" > /proc/mi_modules/mi_sensor/mi_sensor0
                echo "HTTP/1.1 200 OK"
                echo "Content-type: text/plain"
                echo ""
                echo "$POST_fps"
                exit
            fi
            ;;
        setbitrate)
            if echo "$POST_bitrate" | grep -qE '^[0-9]+$' && [ "$POST_bitrate" -ge 0 ] && [ "$POST_bitrate" -le 8192 ]; then
                curl -s "http://localhost/api/v1/set?video0.bitrate=$POST_bitrate" >/dev/null
                echo "HTTP/1.1 200 OK"
                echo "Content-type: text/plain"
                echo ""
                echo "$POST_bitrate"
                exit
            fi
            ;;
    esac
    exit
fi
%>

<%in p/header.cgi %>

<style>
input[type="range"] {
    outline: none;
    border: none;
    box-shadow: none;
    margin: 15px 0;
}
.control-group {
    margin-bottom: 25px;
}
</style>

<script>
function updateControl(type, value) {
    fetch(window.location.href, {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: `action=set${type}&${type}=${value}`
    })
    .then(response => response.text())
    .then(newValue => {
        document.getElementById(`${type}Value`).textContent = `${newValue}${type === 'fps' ? ' FPS' : ' kbps'}`;
    })
    .catch(error => console.error('Error:', error));
}
</script>

<div class="container mt-5">
    <div class="card border-0">
        <div class="card-body p-3">
            <!-- FPS Control -->
            <div class="control-group">
                <div class="d-flex align-items-center gap-3">
                    <input type="range" 
                           class="form-range" 
                           id="fpsSlider"
                           min="10" 
                           max="60" 
                           value="30"
                           oninput="updateControl('fps', this.value)">
                    <span class="badge bg-primary fs-5" id="fpsValue">30 FPS</span>
                </div>
            </div>

            <!-- Bitrate Control -->
            <div class="control-group">
                <div class="d-flex align-items-center gap-3">
                    <input type="range" 
                           class="form-range" 
                           id="bitrateSlider"
                           min="0" 
                           max="8192" 
                           step="256"
                           value="0"
                           oninput="updateControl('bitrate', this.value)">
                    <span class="badge bg-success fs-5" id="bitrateValue">0 kbps</span>
                </div>
            </div>
        </div>
    </div>
</div>

<%in p/footer.cgi %>