// dist-core/config-core.mjs
var DEFAULT_CONFIG = {
  "TitleBlock": {
    "TitleBlockWidthMm": 51,
    "SheetMarginLeftMm": 12,
    "SheetMarginRightMm": 6,
    "SheetMarginTopMm": 6,
    "SheetMarginBottomMm": 6
  },
  "Keyplan": {
    "Anchor": "BottomRight",
    "OffsetXMm": 0,
    "OffsetYMm": 5,
    "CanvasWidthMm": 60,
    "CanvasHeightMm": 40,
    "LabelFontSizeMm": 2,
    "UseViewplanKeyplan": true,
    "SuppressViewportTitle": true,
    "HighlightLineWeight": 7,
    "HatchSpacingMm": 1.2,
    "HighlightColorHex": "FF0000",
    "HighlightLineStyleName": "KP_Highlight",
    "NormalLineStyleName": "<Medium Lines>",
    "ViewTemplateName": "HW_KEYPLAN",
    "ForceRecreate": true
  },
  "Grid": {
    "EnableGridTrim": true,
    "BubbleExtensionMm": 100,
    "ShowBubbleTop": false,
    "ShowBubbleBotton": false,
    "ShowBubbleRight": true,
    "ShowBubbleLeft": true
  },
  "Viewport": {
    "MinClearanceMm": 10,
    "AutoRotateAspectRatio": 1.5
  },
  "DualView": {
    "Enabled": true,
    "ViewGapMm": 50,
    "PreferHorizontal": true
  },
  "ViewSplitter": {
    "ExtentPaddingXMm": 10,
    "ExtentPaddingYMm": 10,
    "ScaleMin": 50,
    "ScaleMax": 75,
    "MinFillRatio": 0.05,
    "ScaleStep": 5,
    "MinTilePaperMm": 60,
    "UseEnhancedLogic": true
  },
  "Workset": {
    "Name": "91.LINK CAD"
  },
  "PackageTypes": [
    {
      "Key": "CanHo",
      "DisplayName": "C\u0103n h\u1ED9",
      "ModelGroupPatterns": [
        "*"
      ],
      "Sheets": [
        {
          "DrawingType": "ToBia",
          "SourceType": "Cover",
          "DisplayName": "M\u1EB6T B\u1EB0NG H\u1EC6 TH\u1ED0NG C\u1EA4P THO\xC1T N\u01AF\u1EDAC C\u0102N H\u1ED8",
          "Count": 1,
          "IsRequired": true
        },
        {
          "DrawingType": "ToLot",
          "SourceType": "Cover",
          "DisplayName": "M\u1EB6T B\u1EB0NG H\u1EC6 TH\u1ED0NG C\u1EA4P THO\xC1T N\u01AF\u1EDAC C\u0102N H\u1ED8",
          "Count": 1,
          "IsRequired": true
        },
        {
          "DrawingType": "DanhMucBanVe",
          "SourceType": "Index",
          "DisplayName": "Danh m\u1EE5c b\u1EA3n v\u1EBD",
          "Count": 1,
          "IsRequired": true
        },
        {
          "DrawingType": "Legend",
          "SourceType": "Cad",
          "DisplayName": "GHI CH\xDA CHUNG",
          "Count": 1,
          "IsRequired": false
        },
        {
          "DrawingType": "MatBangCombine",
          "SourceType": "Blank",
          "DisplayName": "M\u1EB7t b\u1EB1ng",
          "Count": 1,
          "IsRequired": false
        },
        {
          "DrawingType": "SoDoNguyenLy",
          "SourceType": "Cad",
          "DisplayName": "S\u01A1 \u0111\u1ED3 kh\xF4ng gian",
          "Count": 1,
          "IsRequired": false
        },
        {
          "DrawingType": "MatBangThiCong",
          "SourceType": "Blank",
          "DisplayName": "M\u1EB7t b\u1EB1ng",
          "Count": 1,
          "IsRequired": true
        },
        {
          "DrawingType": "MatBangThiCong",
          "SourceType": "Blank",
          "DisplayName": "M\u1EB7t b\u1EB1ng",
          "Count": 1,
          "IsRequired": true
        },
        {
          "DrawingType": "ChiTietLapDat",
          "SourceType": "Cad",
          "DisplayName": "Chi ti\u1EBFt l\u1EAFp \u0111\u1EB7t",
          "Count": 1,
          "IsRequired": true
        },
        {
          "DrawingType": "ChiTietLapDat",
          "SourceType": "Cad",
          "DisplayName": "Chi ti\u1EBFt l\u1EAFp \u0111\u1EB7t",
          "Count": 1,
          "IsRequired": true
        },
        {
          "DrawingType": "ChiTietLapDat",
          "SourceType": "Cad",
          "DisplayName": "Chi ti\u1EBFt l\u1EAFp \u0111\u1EB7t",
          "Count": 1,
          "IsRequired": true
        }
      ]
    },
    {
      "Key": "HanhlangFCU",
      "DisplayName": "H\xE0nh lang",
      "ModelGroupPatterns": [],
      "Sheets": [
        {
          "DrawingType": "ToBia",
          "SourceType": "Cover",
          "DisplayName": "M\u1EB6T B\u1EB0NG T\u1ED4NG TH\u1EC2 FCU-T\u1EA6NG",
          "Count": 1,
          "IsRequired": true
        },
        {
          "DrawingType": "ToLot",
          "SourceType": "Cover",
          "DisplayName": "M\u1EB6T B\u1EB0NG T\u1ED4NG TH\u1EC2 FCU-T\u1EA6NG",
          "Count": 1,
          "IsRequired": true
        },
        {
          "DrawingType": "DanhMucBanVe",
          "SourceType": "Index",
          "DisplayName": "Danh m\u1EE5c b\u1EA3n v\u1EBD",
          "Count": 1,
          "IsRequired": true
        },
        {
          "DrawingType": "Legend",
          "SourceType": "Cad",
          "DisplayName": "GHI CH\xDA CHUNG",
          "Count": 1,
          "IsRequired": false
        },
        {
          "DrawingType": "MatBangThiCong",
          "SourceType": "Blank",
          "DisplayName": "M\u1EB7t b\u1EB1ng",
          "Count": 1,
          "IsRequired": true
        },
        {
          "DrawingType": "ChiTietLapDat",
          "SourceType": "Cad",
          "DisplayName": "Chi ti\u1EBFt l\u1EAFp \u0111\u1EB7t",
          "Count": 1,
          "IsRequired": true
        },
        {
          "DrawingType": "ChiTietLapDat",
          "SourceType": "Cad",
          "DisplayName": "Chi ti\u1EBFt l\u1EAFp \u0111\u1EB7t",
          "Count": 1,
          "IsRequired": true
        }
      ]
    },
    {
      "Key": "HanhlangHVAC",
      "DisplayName": "H\xE0nh lang",
      "ModelGroupPatterns": [],
      "Sheets": [
        {
          "DrawingType": "ToBia",
          "SourceType": "Cover",
          "DisplayName": "M\u1EB6T B\u1EB0NG H\u1EC6 TH\u1ED0NG \u0110I\u1EC0U H\xD2A KH\xD4NG KH\xCD-T\u1EA6NG",
          "Count": 1,
          "IsRequired": true
        },
        {
          "DrawingType": "ToLot",
          "SourceType": "Cover",
          "DisplayName": "M\u1EB6T B\u1EB0NG H\u1EC6 TH\u1ED0NG \u0110I\u1EC0U H\xD2A KH\xD4NG KH\xCD-T\u1EA6NG",
          "Count": 1,
          "IsRequired": true
        },
        {
          "DrawingType": "DanhMucBanVe",
          "SourceType": "Index",
          "DisplayName": "Danh m\u1EE5c b\u1EA3n v\u1EBD",
          "Count": 1,
          "IsRequired": true
        },
        {
          "DrawingType": "Legend",
          "SourceType": "Cad",
          "DisplayName": "GHI CH\xDA CHUNG",
          "Count": 1,
          "IsRequired": false
        },
        {
          "DrawingType": "MatBangThiCong",
          "SourceType": "Blank",
          "DisplayName": "M\u1EB7t b\u1EB1ng",
          "Count": 1,
          "IsRequired": true
        },
        {
          "DrawingType": "ChiTietLapDat",
          "SourceType": "Cad",
          "DisplayName": "Chi ti\u1EBFt l\u1EAFp \u0111\u1EB7t",
          "Count": 1,
          "IsRequired": true
        },
        {
          "DrawingType": "ChiTietLapDat",
          "SourceType": "Cad",
          "DisplayName": "Chi ti\u1EBFt l\u1EAFp \u0111\u1EB7t",
          "Count": 1,
          "IsRequired": true
        }
      ]
    }
  ]
};
var cloneDefault = () => JSON.parse(JSON.stringify(DEFAULT_CONFIG));
function cleanJsonc(source) {
  let output = "";
  let inString = false;
  let escaped = false;
  for (let index = 0; index < source.length; index += 1) {
    const char = source[index];
    const next = source[index + 1];
    if (inString) {
      output += char;
      if (escaped) escaped = false;
      else if (char === "\\") escaped = true;
      else if (char === '"') inString = false;
      continue;
    }
    if (char === '"') {
      inString = true;
      output += char;
      continue;
    }
    if (char === "/" && next === "/") {
      while (index < source.length && source[index] !== "\n") index += 1;
      output += "\n";
      continue;
    }
    if (char === "/" && next === "*") {
      index += 2;
      while (index < source.length - 1 && !(source[index] === "*" && source[index + 1] === "/")) index += 1;
      index += 1;
      continue;
    }
    if (char === ",") {
      let lookAhead = index + 1;
      while (/\s/.test(source[lookAhead] ?? "")) lookAhead += 1;
      if (source[lookAhead] === "}" || source[lookAhead] === "]") continue;
    }
    output += char;
  }
  return output;
}
function normalizeConfig(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("N\u1ED9i dung g\u1ED1c ph\u1EA3i l\xE0 m\u1ED9t object JSON.");
  const raw = value;
  const packages = Array.isArray(raw.PackageTypes) ? raw.PackageTypes.map((item, index) => {
    const pkg = item && typeof item === "object" ? item : {};
    return {
      ...pkg,
      Key: typeof pkg.Key === "string" ? pkg.Key : "Package" + (index + 1),
      DisplayName: typeof pkg.DisplayName === "string" ? pkg.DisplayName : "B\u1ED9 b\u1EA3n v\u1EBD " + (index + 1),
      ModelGroupPatterns: Array.isArray(pkg.ModelGroupPatterns) ? pkg.ModelGroupPatterns.map(String) : [],
      Sheets: Array.isArray(pkg.Sheets) ? pkg.Sheets.map((sheet) => ({
        ...sheet && typeof sheet === "object" ? sheet : {},
        DrawingType: String(sheet?.DrawingType ?? "NewDrawing"),
        SourceType: String(sheet?.SourceType ?? "Blank"),
        DisplayName: String(sheet?.DisplayName ?? "B\u1EA3n v\u1EBD m\u1EDBi"),
        Count: Number(sheet?.Count ?? 1),
        IsRequired: Boolean(sheet?.IsRequired ?? true)
      })) : []
    };
  }) : cloneDefault().PackageTypes;
  return {
    ...DEFAULT_CONFIG,
    ...raw,
    TitleBlock: { ...DEFAULT_CONFIG.TitleBlock, ...raw.TitleBlock ?? {} },
    Keyplan: { ...DEFAULT_CONFIG.Keyplan, ...raw.Keyplan ?? {} },
    Grid: { ...DEFAULT_CONFIG.Grid, ...raw.Grid ?? {} },
    Viewport: { ...DEFAULT_CONFIG.Viewport, ...raw.Viewport ?? {} },
    DualView: { ...DEFAULT_CONFIG.DualView, ...raw.DualView ?? {} },
    ViewSplitter: { ...DEFAULT_CONFIG.ViewSplitter, ...raw.ViewSplitter ?? {} },
    Workset: { ...DEFAULT_CONFIG.Workset, ...raw.Workset && typeof raw.Workset === "object" && !Array.isArray(raw.Workset) ? raw.Workset : {} },
    PackageTypes: packages
  };
}
function computeStats(config) {
  return {
    packages: config.PackageTypes.length,
    totalSheets: config.PackageTypes.reduce((sum, item) => sum + item.Sheets.reduce((count, sheet) => count + sheet.Count, 0), 0),
    requiredSheets: config.PackageTypes.reduce((sum, item) => sum + item.Sheets.filter((sheet) => sheet.IsRequired).reduce((count, sheet) => count + sheet.Count, 0), 0),
    cadSheets: config.PackageTypes.reduce((sum, item) => sum + item.Sheets.filter((sheet) => sheet.SourceType.toLowerCase() === "cad").reduce((count, sheet) => count + sheet.Count, 0), 0)
  };
}
function validateConfig(config, cadSheetCount = computeStats(config).cadSheets) {
  const issues = [];
  if (config.ViewSplitter.ScaleMin > config.ViewSplitter.ScaleMax) issues.push("ScaleMin ph\u1EA3i nh\u1ECF h\u01A1n ho\u1EB7c b\u1EB1ng ScaleMax.");
  if (!/^[0-9A-Fa-f]{6}$/.test(config.Keyplan.HighlightColorHex.replace("#", ""))) issues.push("M\xE0u highlight ph\u1EA3i c\xF3 \u0111\xFAng 6 k\xFD t\u1EF1 HEX.");
  if (config.DualView.ViewGapMm < 0) issues.push("Kho\u1EA3ng c\xE1ch gi\u1EEFa hai view kh\xF4ng \u0111\u01B0\u1EE3c \xE2m.");
  if (cadSheetCount > 0 && !config.Workset.Name.trim()) issues.push("C\xE1c sheet ngu\u1ED3n Cad c\u1EA7n Workset.Name \u0111\u1EC3 link CAD v\xE0o \u0111\xFAng workset.");
  const keys = config.PackageTypes.map((item) => item.Key.trim()).filter(Boolean);
  if (new Set(keys).size !== keys.length) issues.push("Key c\u1EE7a c\xE1c b\u1ED9 b\u1EA3n v\u1EBD ph\u1EA3i l\xE0 duy nh\u1EA5t.");
  config.PackageTypes.forEach((item) => {
    if (!item.Key.trim()) issues.push("B\u1ED9 \u201C" + (item.DisplayName || "ch\u01B0a \u0111\u1EB7t t\xEAn") + "\u201D \u0111ang thi\u1EBFu Key.");
    if (item.Sheets.some((sheet) => sheet.Count < 1)) issues.push("B\u1ED9 \u201C" + item.DisplayName + "\u201D c\xF3 sheet v\u1EDBi Count nh\u1ECF h\u01A1n 1.");
  });
  return issues;
}
var SECTION_NAMES = ["TitleBlock", "Keyplan", "Grid", "Viewport", "DualView", "ViewSplitter", "Workset"];
function collectWarnings(raw) {
  const warnings = [];
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return warnings;
  const source = raw;
  for (const section of SECTION_NAMES) {
    const value = source[section];
    if (value === void 0) {
      warnings.push("Thi\u1EBFu nh\xF3m " + section + ", \u0111\xE3 d\xF9ng to\xE0n b\u1ED9 gi\xE1 tr\u1ECB m\u1EB7c \u0111\u1ECBnh.");
      continue;
    }
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      warnings.push("Nh\xF3m " + section + " kh\xF4ng ph\u1EA3i object, \u0111\xE3 d\xF9ng to\xE0n b\u1ED9 gi\xE1 tr\u1ECB m\u1EB7c \u0111\u1ECBnh.");
      continue;
    }
    const missing = Object.keys(DEFAULT_CONFIG[section]).filter((key) => value[key] === void 0);
    if (missing.length > 0) warnings.push("Nh\xF3m " + section + " thi\u1EBFu field: " + missing.join(", ") + ".");
  }
  if (!Array.isArray(source.PackageTypes)) {
    warnings.push("PackageTypes thi\u1EBFu ho\u1EB7c kh\xF4ng ph\u1EA3i m\u1EA3ng, \u0111\xE3 d\xF9ng " + DEFAULT_CONFIG.PackageTypes.length + " b\u1ED9 b\u1EA3n v\u1EBD m\u1EABu c\u1EE7a template.");
  } else {
    source.PackageTypes.forEach((item, index) => {
      const label = "PackageTypes[" + index + "]";
      if (!item || typeof item !== "object" || Array.isArray(item)) {
        warnings.push(label + " kh\xF4ng ph\u1EA3i object, \u0111\xE3 thay b\u1EB1ng b\u1ED9 r\u1ED7ng m\u1EB7c \u0111\u1ECBnh.");
        return;
      }
      const pkg = item;
      if (typeof pkg.Key !== "string") warnings.push(label + " thi\u1EBFu Key, \u0111\xE3 \u0111\u1EB7t th\xE0nh \u201CPackage" + (index + 1) + "\u201D.");
      if (typeof pkg.DisplayName !== "string") warnings.push(label + " thi\u1EBFu DisplayName, \u0111\xE3 \u0111\u1EB7t th\xE0nh \u201CB\u1ED9 b\u1EA3n v\u1EBD " + (index + 1) + "\u201D.");
      if (!Array.isArray(pkg.ModelGroupPatterns)) warnings.push(label + " thi\u1EBFu ModelGroupPatterns, \u0111\xE3 \u0111\u1EB7t th\xE0nh m\u1EA3ng r\u1ED7ng.");
      if (!Array.isArray(pkg.Sheets)) warnings.push(label + " thi\u1EBFu Sheets, \u0111\xE3 \u0111\u1EB7t th\xE0nh m\u1EA3ng r\u1ED7ng.");
    });
  }
  return warnings;
}
function processSource(source, options = {}) {
  const raw = JSON.parse(cleanJsonc(source));
  const config = normalizeConfig(raw);
  const warnings = collectWarnings(raw);
  const stats = computeStats(config);
  const issues = validateConfig(config, stats.cadSheets);
  if (options.strict) issues.push(...warnings);
  return {
    ok: issues.length === 0,
    config,
    json: options.pretty === false ? JSON.stringify(config) : JSON.stringify(config, null, 2),
    issues,
    warnings,
    stats
  };
}

// server/api.mjs
var MAX_BODY_BYTES = 2 * 1024 * 1024;
var CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
  "Access-Control-Max-Age": "86400"
};
function json(status, payload) {
  return new Response(JSON.stringify(payload, null, 2), {
    status,
    headers: { ...CORS_HEADERS, "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" }
  });
}
async function readLimitedText(request) {
  const declared = Number(request.headers.get("content-length") ?? 0);
  if (declared > MAX_BODY_BYTES) return null;
  if (!request.body) return "";
  const reader = request.body.getReader();
  const chunks = [];
  let size = 0;
  for (; ; ) {
    const { done, value } = await reader.read();
    if (done) break;
    size += value.byteLength;
    if (size > MAX_BODY_BYTES) {
      await reader.cancel();
      return null;
    }
    chunks.push(value);
  }
  const merged = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) {
    merged.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return new TextDecoder().decode(merged);
}
function extractSource(body2, contentType) {
  if (!contentType.includes("application/json")) return body2;
  try {
    const parsed = JSON.parse(body2);
    if (parsed && typeof parsed === "object" && typeof parsed.source === "string") return parsed.source;
  } catch {
  }
  return body2;
}
function handleNormalize(body2, contentType, url) {
  const source = extractSource(body2, contentType);
  if (!source.trim()) return json(400, { ok: false, error: "Body r\u1ED7ng. G\u1EEDi n\u1ED9i dung JSON/JSONC trong request body." });
  let result;
  try {
    result = processSource(source, {
      strict: url.searchParams.get("strict") === "1",
      pretty: url.searchParams.get("pretty") !== "0"
    });
  } catch (error) {
    return json(400, { ok: false, error: error instanceof Error ? error.message : "Kh\xF4ng \u0111\u1ECDc \u0111\u01B0\u1EE3c n\u1ED9i dung JSON/JSONC." });
  }
  return json(result.ok ? 200 : 422, result);
}
function handleValidate(body2) {
  let config;
  try {
    config = normalizeConfig(JSON.parse(body2));
  } catch (error) {
    return json(400, { ok: false, error: error instanceof Error ? error.message : "Body kh\xF4ng ph\u1EA3i JSON h\u1EE3p l\u1EC7." });
  }
  const stats = computeStats(config);
  const issues = validateConfig(config, stats.cadSheets);
  return json(issues.length === 0 ? 200 : 422, { ok: issues.length === 0, issues, stats });
}
async function handleApi(request, { version: version2 = "unknown" } = {}) {
  const url = new URL(request.url);
  if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS_HEADERS });
  if (url.pathname === "/api/health") {
    if (request.method !== "GET") return json(405, { ok: false, error: "Ch\u1EC9 h\u1ED7 tr\u1EE3 GET." });
    return json(200, { ok: true, version: version2, time: (/* @__PURE__ */ new Date()).toISOString() });
  }
  if (url.pathname === "/api/template") {
    if (request.method !== "GET") return json(405, { ok: false, error: "Ch\u1EC9 h\u1ED7 tr\u1EE3 GET." });
    return json(200, DEFAULT_CONFIG);
  }
  if (url.pathname === "/api/normalize" || url.pathname === "/api/validate") {
    if (request.method !== "POST") return json(405, { ok: false, error: "Ch\u1EC9 h\u1ED7 tr\u1EE3 POST." });
    const body2 = await readLimitedText(request);
    if (body2 === null) return json(413, { ok: false, error: "Body v\u01B0\u1EE3t qu\xE1 2 MB." });
    return url.pathname === "/api/normalize" ? handleNormalize(body2, request.headers.get("content-type") ?? "", url) : handleValidate(body2);
  }
  return json(404, { ok: false, error: "Kh\xF4ng c\xF3 endpoint " + url.pathname + "." });
}

// server/cli.mjs
function readStdin() {
  return new Promise((resolve, reject) => {
    if (process.stdin.isTTY) return resolve("");
    const chunks = [];
    process.stdin.on("data", (chunk) => chunks.push(chunk));
    process.stdin.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    process.stdin.on("error", reject);
  });
}
var [, , method = "GET", target = "/api/health", headersJson = "{}", version = "unknown"] = process.argv;
var headers = {};
try {
  headers = JSON.parse(headersJson);
} catch {
}
var body = method === "GET" || method === "HEAD" ? void 0 : await readStdin();
try {
  const response = await handleApi(new Request("http://cli" + target, { method, headers, body }), { version });
  process.stdout.write(JSON.stringify({ status: response.status, body: await response.text() }));
} catch (error) {
  process.stdout.write(JSON.stringify({
    status: 500,
    body: JSON.stringify({ ok: false, error: error instanceof Error ? error.message : "L\u1ED7i kh\xF4ng x\xE1c \u0111\u1ECBnh." })
  }));
  process.exitCode = 1;
}
