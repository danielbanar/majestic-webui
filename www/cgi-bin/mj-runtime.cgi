#!/usr/bin/haserl
<%in p/common.cgi %>

<%
page_title="Camera runtime settings"

# Function to parse available resolutions and their max FPS from sensor data
get_available_resolutions() {
    sensor_data=$(cat /proc/mi_modules/mi_sensor/mi_sensor0 2>/dev/null)
    echo "$sensor_data" | awk '/start dump Pad info/,/End dump Pad info/ {
        if (/^[[:space:]]+[0-9]+x[0-9]+@[0-9]+fps/) {
            split($1, res, "@")
            split(res[2], fps, "fps")
            print res[1] "," fps[1]
        }
    }'
}

# Function to parse current resolution and FPS from sensor data
get_current_resolution() {
    sensor_data=$(cat /proc/mi_modules/mi_sensor/mi_sensor0 2>/dev/null)
    echo "$sensor_data" | awk '/start dump Pad info/,/End dump Pad info/ {
        if (/^[[:space:]]+Cur/) {
            split($2, res, "@")
            split(res[2], fps, "fps")
            print res[1] "," fps[1]
        }
    }'
}

if [ "$REQUEST_METHOD" = "POST" ]; then
    case "$POST_action" in
        setfps)
            if echo "$POST_fps" | grep -qE '^[0-9]+$' && [ "$POST_fps" -ge 3 ] && [ "$POST_fps" -le 120 ]; then
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
        setresolution)
            # Parse resolution and max FPS from the posted value
            IFS=',' read -r resolution max_fps <<EOF
$POST_resolution
EOF
            valid_resolutions=$(get_available_resolutions)
            if echo "$valid_resolutions" | grep -q "$resolution,"; then
                # Set the resolution
                yaml-cli -s .video0.size "$resolution"
                # Set the max FPS for this resolution
                yaml-cli -s .video0.fps "$max_fps"
                # Also update the sensor FPS
                echo "setfps 0 $max_fps" > /proc/mi_modules/mi_sensor/mi_sensor0
                
                echo "HTTP/1.1 200 OK"
                echo "Content-type: text/plain"
                echo ""
                echo "$resolution,$max_fps"
                exit
            fi
            ;;
        restartmajestic)
            if killall -1 majestic; then
                echo "HTTP/1.1 200 OK"
                echo "Content-type: text/plain"
                echo ""
                echo "Service restarted successfully"
                exit
            else
                echo "HTTP/1.1 500 Internal Server Error"
                echo "Content-type: text/plain"
                echo ""
                echo "Failed to restart service"
                exit
            fi
            ;;
    esac
    exit
fi

# Get current values for page render
current_resolution_fps=$(get_current_resolution)
available_resolutions=$(get_available_resolutions)

# Parse current resolution and FPS
IFS=',' read -r current_resolution current_fps <<EOF
$current_resolution_fps
EOF

# If we couldn't get current values, set defaults
if [ -z "$current_resolution" ]; then
    current_resolution="1920x1080"
fi
if [ -z "$current_fps" ]; then
    current_fps=30
fi
%>

<%in p/header.cgi %>

<style>
input[type="range"], select {
    outline: none;
    border: none;
    box-shadow: none;
    margin: 15px 0;
}
.control-group {
    margin-bottom: 25px;
}
.resolution-select {
    width: 100%;
    padding: 8px;
    border-radius: 4px;
    border: 1px solid #ddd;
}
.button_submit {
    margin-top: 20px;
    width: 100%;
    padding: 10px;
    background-color: #dc3545;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
}
.button_submit:hover {
    background-color: #c82333;
}
.loading {
    opacity: 0.7;
    pointer-events: none;
}
.badge.updating {
    background-color: #6c757d !important;
}
.info-text {
    font-size: 0.85rem;
    color: #6c757d;
    margin-top: 5px;
}
.sensor-mode-label {
    font-weight: bold;
    margin-bottom: 8px;
}
</style>

<script>
// Debounce function to limit how often a function can be called
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Update control with debouncing (for cases where you might want intermediate updates)
const debouncedUpdateControl = debounce(updateControl, 500);

function updateControl(type, value) {
    const valueElement = document.getElementById(`${type}Value`);
    valueElement.classList.add('updating');
    
    fetch(window.location.href, {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: `action=set${type}&${type}=${value}`
    })
    .then(response => response.text())
    .then(newValue => {
        valueElement.textContent = `${newValue}${type === 'fps' ? ' FPS' : ' kbps'}`;
        valueElement.classList.remove('updating');
    })
    .catch(error => {
        console.error('Error:', error);
        valueElement.classList.remove('updating');
    });
}

function setResolution(value) {
    const resolutionElement = document.getElementById('currentResolution');
    resolutionElement.classList.add('updating');
    
    // Parse the value to get resolution and max FPS
    const [resolution, maxFps] = value.split(',');
    
    fetch(window.location.href, {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: `action=setresolution&resolution=${value}`
    })
    .then(response => response.text())
    .then(res => {
        resolutionElement.textContent = resolution;
        resolutionElement.classList.remove('updating');
        
        // Update FPS slider to match the new resolution's max FPS
        const fpsSlider = document.getElementById('fpsSlider');
        fpsSlider.max = maxFps;
        fpsSlider.value = maxFps;
        document.getElementById('fpsValue').textContent = `${maxFps} FPS`;
        
        // Show the new max FPS in the info text
        document.getElementById('fpsInfo').textContent = `Max FPS for this resolution: ${maxFps}`;
    })
    .catch(error => {
        console.error('Error:', error);
        resolutionElement.classList.remove('updating');
    });
}

function restartService() {
    const button = document.querySelector('.button_submit');
    const originalText = button.textContent;
    
    button.classList.add('loading');
    button.textContent = 'Restarting...';
    
    fetch(window.location.href, {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: 'action=restartmajestic'
    })
    .then(response => response.text())
    .then(result => {
        alert(result);
        button.classList.remove('loading');
        button.textContent = originalText;
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to restart service');
        button.classList.remove('loading');
        button.textContent = originalText;
    });
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
                           min="3" 
                           max="<%= $current_fps %>" 
                           value="<%= $current_fps %>"
                           onchange="updateControl('fps', this.value)"
                           oninput="document.getElementById('fpsValue').textContent = this.value + ' FPS'">
                    <span class="badge bg-primary fs-5" id="fpsValue"><%= $current_fps %> FPS</span>
                </div>
                <div class="info-text" id="fpsInfo">
                    Max FPS for this resolution: <%= $current_fps %>
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
                           onchange="updateControl('bitrate', this.value)"
                           oninput="document.getElementById('bitrateValue').textContent = this.value + ' kbps'">
                    <span class="badge bg-success fs-5" id="bitrateValue">0 kbps</span>
                </div>
            </div>

            <!-- Sensor Modes Selector -->
            <div class="control-group">
                <div class="sensor-mode-label">Sensor Modes:</div>
                <select class="resolution-select" onchange="setResolution(this.value)">
                    <%
                    # Generate options using shell code
                    IFS='
                    '
                    for res_line in $available_resolutions; do
                        IFS=',' read -r res fps <<EOF
$res_line
EOF
                        if [ "$res" = "$current_resolution" ]; then
                            echo "<option value=\"$res,$fps\" selected>$res@${fps}fps</option>"
                        else
                            echo "<option value=\"$res,$fps\">$res@${fps}fps</option>"
                        fi
                    done
                    %>
                </select>
                <div class="mt-2">
                    Current: <span class="badge bg-info" id="currentResolution"><%= $current_resolution %></span>
                </div>
            </div>

            <!-- Restart Service Button -->
            <div class="control-group">
                <button class="button_submit" onclick="restartService()">
                    Restart Majestic
                </button>
            </div>
        </div>
    </div>
</div>

<%in p/footer.cgi %>