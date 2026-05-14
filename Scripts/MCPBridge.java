import org.dreambot.api.script.AbstractScript;
import org.dreambot.api.script.Category;
import org.dreambot.api.script.ScriptManifest;
import org.dreambot.api.methods.map.Tile;
import org.dreambot.api.methods.skills.Skill;
import org.dreambot.api.methods.tabs.Tab;
import org.dreambot.api.methods.input.Camera;
import org.dreambot.api.methods.interactive.GameObjects;
import org.dreambot.api.methods.interactive.NPCs;
import org.dreambot.api.methods.interactive.Players;
import org.dreambot.api.wrappers.interactive.GameObject;
import org.dreambot.api.wrappers.interactive.NPC;
import org.dreambot.api.wrappers.items.GroundItem;
import org.dreambot.api.methods.ground.GroundItems;
import org.dreambot.api.methods.inventory.Inventory;
import org.dreambot.api.utilities.Logger;

import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

@ScriptManifest(
    name = "MCPBridge",
    author = "OpenClaw",
    version = 1.0,
    category = Category.MISC,
    description = "HTTP API bridge for MCP control (zero dependencies)"
)
public class MCPBridge extends AbstractScript {

    private ServerSocket serverSocket;
    private volatile boolean apiRunning = true;
    private Thread acceptThread;

    @Override
    public void onStart() {
        log("MCPBridge: Starting HTTP API on 127.0.0.1:19132");
        try {
            serverSocket = new ServerSocket(19132, 50, InetAddress.getByName("127.0.0.1"));
            serverSocket.setSoTimeout(100);
            acceptThread = new Thread(this::acceptLoop, "MCPBridge-Accept");
            acceptThread.setDaemon(true);
            acceptThread.start();
            log("MCPBridge: HTTP API live on http://127.0.0.1:19132");
        } catch (IOException e) {
            log("MCPBridge: Failed to bind port: " + e.getMessage());
        }
    }

    private void acceptLoop() {
        while (apiRunning && !serverSocket.isClosed()) {
            try {
                Socket client = serverSocket.accept();
                client.setSoTimeout(3000);
                new Thread(() -> handleClient(client), "MCPBridge-Handle").start();
            } catch (SocketTimeoutException e) {
                // Normal, just re-loop
            } catch (IOException e) {
                if (apiRunning) log("MCPBridge accept error: " + e.getMessage());
            }
        }
    }

    @Override
    public int onLoop() {
        return 600;
    }

    @Override
    public void onExit() {
        apiRunning = false;
        try { if (serverSocket != null) serverSocket.close(); } catch (IOException e) {}
        log("MCPBridge: Stopped");
    }

    // --- HTTP handling ---

    private void handleClient(Socket client) {
        try {
            BufferedReader in = new BufferedReader(new InputStreamReader(client.getInputStream(), StandardCharsets.UTF_8));
            OutputStream out = client.getOutputStream();

            // Parse request line
            String requestLine = in.readLine();
            if (requestLine == null) { client.close(); return; }

            String[] parts = requestLine.split(" ");
            if (parts.length < 2) { client.close(); return; }
            String path = parts[1];

            // Skip headers
            String line;
            while ((line = in.readLine()) != null && !line.isEmpty()) {}

            // Route
            String body = routeRequest(path);
            byte[] bodyBytes = body.getBytes(StandardCharsets.UTF_8);

            String headers = "HTTP/1.1 200 OK\r\n" +
                "Content-Type: application/json\r\n" +
                "Access-Control-Allow-Origin: *\r\n" +
                "Content-Length: " + bodyBytes.length + "\r\n" +
                "Connection: close\r\n\r\n";

            out.write(headers.getBytes(StandardCharsets.UTF_8));
            out.write(bodyBytes);
            out.flush();
            client.close();
        } catch (Exception e) {
            try { client.close(); } catch (IOException ex) {}
        }
    }

    private String routeRequest(String fullPath) {
        try {
            String[] urlParts = fullPath.split("\\?", 2);
            String path = urlParts[0];
            String query = urlParts.length > 1 ? urlParts[1] : "";
            Map<String, String> params = parseParams(query);

            switch (path) {
                case "/api/status":     return apiStatus();
                case "/api/player":     return apiPlayer();
                case "/api/inventory":  return apiInventory();
                case "/api/skills":     return apiSkills();
                case "/api/npcs":       return apiNpcs(params);
                case "/api/objects":    return apiObjects(params);
                case "/api/grounditems": return apiGroundItems(params);
                case "/api/camera":     return apiCamera(params);
                case "/api/navigate":   return apiNavigate(params);
                case "/api/interact":   return apiInteract(params);
                case "/api/inventory-action": return apiInventoryAction(params);
                case "/api/tab":        return apiTab(params);
                case "/api/chat":       return apiChat(params);
                case "/api/stop":       return apiStop();
                default:                return err("Unknown endpoint: " + path);
            }
        } catch (Exception e) {
            return err("Internal error: " + e.getMessage());
        }
    }

    // --- Query parsing ---

    private Map<String, String> parseParams(String query) {
        Map<String, String> map = new LinkedHashMap<>();
        if (query == null || query.isEmpty()) return map;
        for (String pair : query.split("&")) {
            String[] kv = pair.split("=", 2);
            if (kv.length == 2) {
                try {
                    map.put(URLDecoder.decode(kv[0], "UTF-8"), URLDecoder.decode(kv[1], "UTF-8"));
                } catch (Exception e) {
                    map.put(kv[0], kv[1]);
                }
            }
        }
        return map;
    }

    // --- JSON helpers ---

    private String q(String s) {
        if (s == null) return "null";
        return "\"" + s.replace("\\", "\\\\").replace("\"", "\\\"")
                       .replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t") + "\"";
    }

    private String tile(Tile t) {
        return String.format("{\"x\":%d,\"y\":%d,\"z\":%d}", t.getX(), t.getY(), t.getZ());
    }

    private String err(String msg) {
        return "{\"error\":" + q(msg) + "}";
    }

    // --- API endpoints ---

    private String apiStatus() {
        boolean loggedIn = getLocalPlayer() != null && getLocalPlayer().exists();
        String name = loggedIn ? getLocalPlayer().getName() : null;
        return String.format("{\"status\":\"running\",\"loggedIn\":%b,\"playerName\":%s,\"version\":\"1.0\"}",
            loggedIn, q(name));
    }

    private String apiPlayer() {
        var p = getLocalPlayer();
        if (p == null) return err("no player");
        return String.format(
            "{\"name\":%s,\"tile\":%s,\"health\":%d,\"animation\":%d,\"isMoving\":%b,\"isAnimating\":%b}",
            q(p.getName()), tile(p.getTile()), p.getHealthPercentage(),
            p.getAnimation(), p.isMoving(), p.isAnimating());
    }

    private String apiInventory() {
        var items = Inventory.all();
        StringBuilder sb = new StringBuilder("[");
        boolean first = true;
        for (var item : items) {
            if (!first) sb.append(",");
            first = false;
            sb.append(String.format("{\"name\":%s,\"id\":%d,\"amount\":%d,\"slot\":%d}",
                q(item.getName()), item.getID(), item.getAmount(), item.getSlot()));
        }
        sb.append("]");
        return String.format("{\"count\":%d,\"items\":%s}", items.size(), sb);
    }

    private String apiSkills() {
        StringBuilder sb = new StringBuilder("{");
        boolean first = true;
        for (Skill s : Skill.values()) {
            if (!first) sb.append(",");
            first = false;
            sb.append(String.format("\"%s\":{\"level\":%d,\"xp\":%d,\"boosted\":%d}",
                s.name().toLowerCase(),
                getSkills().getRealLevel(s),
                getSkills().getExperience(s),
                getSkills().getBoostedLevel(s)));
        }
        sb.append("}");
        return sb.toString();
    }

    private String apiNpcs(Map<String, String> params) {
        int radius = Integer.parseInt(params.getOrDefault("radius", "10"));
        String nf = params.getOrDefault("name", "").toLowerCase();
        List<NPC> npcs = NPCs.all(n ->
            n != null && n.exists() && n.distance() <= radius &&
            (nf.isEmpty() || n.getName().toLowerCase().contains(nf)));
        StringBuilder sb = new StringBuilder("[");
        boolean first = true;
        for (NPC n : npcs) {
            if (!first) sb.append(",");
            first = false;
            sb.append(String.format("{\"name\":%s,\"id\":%d,\"tile\":%s,\"distance\":%d,\"combat\":%d}",
                q(n.getName()), n.getID(), tile(n.getTile()), (int)n.distance(), n.getCombatLevel()));
        }
        sb.append("]");
        return String.format("{\"count\":%d,\"npcs\":%s}", npcs.size(), sb);
    }

    private String apiObjects(Map<String, String> params) {
        int radius = Integer.parseInt(params.getOrDefault("radius", "10"));
        String nf = params.getOrDefault("name", "").toLowerCase();
        List<GameObject> objs = GameObjects.all(o ->
            o != null && o.exists() && o.distance() <= radius &&
            (nf.isEmpty() || o.getName().toLowerCase().contains(nf)));
        StringBuilder sb = new StringBuilder("[");
        boolean first = true;
        for (GameObject o : objs) {
            if (!first) sb.append(",");
            first = false;
            String[] acts = o.getActions();
            String actStr = acts != null ? String.join(",", acts) : "";
            sb.append(String.format("{\"name\":%s,\"id\":%d,\"tile\":%s,\"distance\":%d,\"actions\":%s}",
                q(o.getName()), o.getID(), tile(o.getTile()), (int)o.distance(), q(actStr)));
        }
        sb.append("]");
        return String.format("{\"count\":%d,\"objects\":%s}", objs.size(), sb);
    }

    private String apiGroundItems(Map<String, String> params) {
        int radius = Integer.parseInt(params.getOrDefault("radius", "10"));
        String nf = params.getOrDefault("name", "").toLowerCase();
        List<GroundItem> items = GroundItems.all(i ->
            i != null && i.exists() && i.distance() <= radius &&
            (nf.isEmpty() || i.getName().toLowerCase().contains(nf)));
        StringBuilder sb = new StringBuilder("[");
        boolean first = true;
        for (GroundItem gi : items) {
            if (!first) sb.append(",");
            first = false;
            sb.append(String.format("{\"name\":%s,\"id\":%d,\"tile\":%s,\"amount\":%d}",
                q(gi.getName()), gi.getID(), tile(gi.getTile()), gi.getAmount()));
        }
        sb.append("]");
        return String.format("{\"count\":%d,\"items\":%s}", items.size(), sb);
    }

    private String apiCamera(Map<String, String> params) {
        String action = params.getOrDefault("action", "get");
        switch (action) {
            case "rotate": {
                int yaw = Integer.parseInt(params.getOrDefault("yaw", "0"));
                int pitch = Integer.parseInt(params.getOrDefault("pitch", "0"));
                Camera.rotateTo(yaw, pitch);
                return String.format("{\"ok\":true,\"yaw\":%d,\"pitch\":%d}", yaw, pitch);
            }
            case "up":
                Camera.rotateTo(Camera.getYaw(), Math.min(Camera.getPitch() + 30, 255));
                return "{\"ok\":true,\"action\":\"up\"}";
            case "down":
                Camera.rotateTo(Camera.getYaw(), Math.max(Camera.getPitch() - 30, 0));
                return "{\"ok\":true,\"action\":\"down\"}";
            default:
                return String.format("{\"yaw\":%d,\"pitch\":%d}", Camera.getYaw(), Camera.getPitch());
        }
    }

    private String apiNavigate(Map<String, String> params) {
        int x = Integer.parseInt(params.get("x"));
        int y = Integer.parseInt(params.get("y"));
        int z = Integer.parseInt(params.getOrDefault("z", "0"));
        Tile target = new Tile(x, y, z);
        boolean ok = getWalking().walk(target);
        return String.format("{\"ok\":%b,\"target\":%s,\"distance\":%d}", ok, tile(target), (int)target.distance());
    }

    private String apiInteract(Map<String, String> params) {
        String type = params.getOrDefault("type", "npc");
        String name = params.getOrDefault("name", "");
        String action = params.getOrDefault("action", "");
        int radius = Integer.parseInt(params.getOrDefault("radius", "15"));
        boolean result = false;
        String target = "";

        if ("npc".equals(type)) {
            NPC npc = NPCs.closest(n -> n != null && n.exists() && n.distance() <= radius &&
                (name.isEmpty() || n.getName().toLowerCase().contains(name.toLowerCase())));
            if (npc != null) {
                target = npc.getName();
                result = action.isEmpty() ? npc.interact() : npc.interact(action);
            }
        } else if ("object".equals(type)) {
            GameObject obj = GameObjects.closest(o -> o != null && o.exists() && o.distance() <= radius &&
                (name.isEmpty() || o.getName().toLowerCase().contains(name.toLowerCase())));
            if (obj != null) {
                target = obj.getName();
                result = action.isEmpty() ? obj.interact() : obj.interact(action);
            }
        } else if ("grounditem".equals(type)) {
            GroundItem gi = GroundItems.closest(i -> i != null && i.exists() && i.distance() <= radius &&
                (name.isEmpty() || i.getName().toLowerCase().contains(name.toLowerCase())));
            if (gi != null) {
                target = gi.getName();
                result = action.isEmpty() ? gi.interact() : gi.interact(action);
            }
        }
        return String.format("{\"ok\":%b,\"target\":%s,\"action\":%s}", result, q(target), q(action));
    }

    private String apiInventoryAction(Map<String, String> params) {
        String name = params.getOrDefault("name", "");
        String action = params.getOrDefault("action", "Use");
        int id = Integer.parseInt(params.getOrDefault("id", "-1"));
        boolean result = false;
        String target = "";

        if (id >= 0) {
            var item = Inventory.get(id);
            if (item != null) {
                target = item.getName();
                result = action.isEmpty() ? item.interact() : item.interact(action);
            }
        } else if (!name.isEmpty()) {
            var item = Inventory.get(i -> i != null && i.getName().toLowerCase().contains(name.toLowerCase()));
            if (item != null) {
                target = item.getName();
                result = action.isEmpty() ? item.interact() : item.interact(action);
            }
        }
        return String.format("{\"ok\":%b,\"item\":%s,\"action\":%s}", result, q(target), q(action));
    }

    private String apiTab(Map<String, String> params) {
        String tabName = params.getOrDefault("tab", "inventory").toUpperCase();
        try {
            Tab tab = Tab.valueOf(tabName);
            getTabs().open(tab);
            return String.format("{\"ok\":true,\"tab\":%s}", q(tabName));
        } catch (IllegalArgumentException e) {
            return err("Invalid tab: " + tabName);
        }
    }

    private String apiChat(Map<String, String> params) {
        String text = params.get("text");
        if (text != null && !text.isEmpty()) {
            getKeyboard().type(text, true);
            return String.format("{\"ok\":true,\"sent\":%s}", q(text));
        }
        return err("no text provided");
    }

    private String apiStop() {
        stop();
        return "{\"ok\":true,\"action\":\"stopping\"}";
    }
}
