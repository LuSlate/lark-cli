#!/usr/bin/env node
// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

import { createHash } from "node:crypto";
import { createRequire } from "node:module";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

const SCRIPT_DIR = path.dirname(new URL(import.meta.url).pathname);
const REPO_ROOT = path.resolve(SCRIPT_DIR, "..", "..", "..");
const REFERENCES_DIR = path.resolve(SCRIPT_DIR, "..", "references");
const SOURCE_ROOT = "/Users/bytedance/bd-projects/beautiful-html-templates";
const DEFAULT_MANIFEST = path.join(REFERENCES_DIR, "production-review", "beautiful", "manifest.json");
const DEFAULT_OUTPUT_DIR = path.join(REFERENCES_DIR, "production-review", "beautiful", "source-page-screenshots");
const DEFAULT_RECEIPT = path.join(REFERENCES_DIR, "receipts", "production-review", "beautiful-34-source-page-screenshots.json");
const DEFAULT_NODE_MODULES = "/Users/bytedance/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules";
const DEFAULT_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

function parseArgs(argv) {
  const args = {
    manifest: DEFAULT_MANIFEST,
    outputDir: DEFAULT_OUTPUT_DIR,
    receipt: DEFAULT_RECEIPT,
    nodeModules: process.env.SVGLIDE_NODE_MODULES || DEFAULT_NODE_MODULES,
    chrome: process.env.SVGLIDE_CHROME || DEFAULT_CHROME,
    family: "",
    quality: 86,
    width: 960,
    height: 540,
    pretty: false,
  };
  for (let index = 2; index < argv.length; index += 1) {
    const item = argv[index];
    if (item === "--manifest") args.manifest = argv[++index];
    else if (item === "--output-dir") args.outputDir = argv[++index];
    else if (item === "--receipt") args.receipt = argv[++index];
    else if (item === "--node-modules") args.nodeModules = argv[++index];
    else if (item === "--chrome") args.chrome = argv[++index];
    else if (item === "--family") args.family = argv[++index];
    else if (item === "--quality") args.quality = Number(argv[++index]);
    else if (item === "--width") args.width = Number(argv[++index]);
    else if (item === "--height") args.height = Number(argv[++index]);
    else if (item === "--pretty") args.pretty = true;
    else throw new Error(`unknown argument: ${item}`);
  }
  return args;
}

function slug(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "") || "page";
}

function relpath(filePath) {
  return path.relative(REPO_ROOT, filePath).split(path.sep).join("/");
}

function sha256(buffer) {
  return createHash("sha256").update(buffer).digest("hex");
}

function screenshotPath(outputDir, familyId, sourceSlideIndex, variantId) {
  return path.join(outputDir, familyId, `${String(sourceSlideIndex).padStart(3, "0")}-${slug(variantId)}.jpg`);
}

async function readJson(filePath) {
  return JSON.parse(await readFile(filePath, "utf8"));
}

function loadPlaywright(nodeModules) {
  const requireFromBundle = createRequire(`${nodeModules}/`);
  return requireFromBundle("playwright");
}

async function setActiveSlide(page, slideIndex, sourceClass) {
  return await page.evaluate(({ index, className }) => {
    const slides = Array.from(document.querySelectorAll(".slide")).length
      ? Array.from(document.querySelectorAll(".slide"))
      : Array.from(document.querySelectorAll("section[data-screen-label]"));
    let activeIndex = index;
    if (className) {
      const classMatchIndex = slides.findIndex((slide) => slide.classList.contains(className));
      if (classMatchIndex >= 0) activeIndex = classMatchIndex;
    }
    slides.forEach((slide, position) => {
      slide.classList.toggle("active", position === activeIndex);
      slide.classList.toggle("is-active", position === activeIndex);
      slide.classList.toggle("prev", position < activeIndex);
      slide.removeAttribute("aria-hidden");
      slide.removeAttribute("data-deck-active");
      slide.removeAttribute("data-svglide-capture-active");
      if (position === activeIndex) {
        slide.setAttribute("data-deck-active", "");
        slide.setAttribute("data-svglide-capture-active", "");
        slide.style.opacity = "1";
        slide.style.visibility = "visible";
        slide.style.pointerEvents = "auto";
        slide.style.transform = "translateX(0)";
        slide.style.zIndex = "10";
      } else {
        slide.style.opacity = "0";
        slide.style.visibility = "hidden";
        slide.style.pointerEvents = "none";
        slide.style.zIndex = "0";
      }
    });
    const current = document.getElementById("current");
    const total = document.getElementById("total");
    const progress = document.getElementById("progress");
    if (current) current.textContent = String(activeIndex + 1);
    if (total) total.textContent = String(slides.length);
    if (progress) progress.style.width = `${((activeIndex + 1) / Math.max(slides.length, 1)) * 100}%`;
    return { activeIndex, slideCount: slides.length };
  }, { index: slideIndex, className: sourceClass || "" });
}

async function createCaptureRoot(page, activeIndex, args) {
  return await page.evaluate(({ index, width, height }) => {
    const existing = document.getElementById("svglide-source-capture-root");
    if (existing) existing.remove();

    const slides = Array.from(document.querySelectorAll(".slide")).length
      ? Array.from(document.querySelectorAll(".slide"))
      : Array.from(document.querySelectorAll("section[data-screen-label]"));
    const source = slides[index];
    if (!source) {
      return { ok: false, reason: "active_slide_not_found", selector: "#svglide-source-capture-root" };
    }

    const computed = window.getComputedStyle(source);
    const bodyComputed = window.getComputedStyle(document.body);
    const sourceBackground = computed.backgroundColor || "";
    const bodyBackground = bodyComputed.backgroundColor || "#fff";
    const background =
      sourceBackground && sourceBackground !== "rgba(0, 0, 0, 0)" && sourceBackground !== "transparent"
        ? sourceBackground
        : bodyBackground;

    const root = document.createElement("div");
    root.id = "svglide-source-capture-root";
    root.setAttribute("data-svglide-source-capture-root", "");
    Object.assign(root.style, {
      position: "fixed",
      left: "0",
      top: "0",
      width: `${width}px`,
      height: `${height}px`,
      margin: "0",
      padding: "0",
      overflow: "hidden",
      background,
      zIndex: "2147483647",
      pointerEvents: "none",
      boxSizing: "border-box",
    });

    const clone = source.cloneNode(true);
    clone.classList.add("active", "is-active");
    clone.classList.remove("prev");
    clone.setAttribute("data-deck-active", "");
    clone.setAttribute("data-svglide-capture-active", "");
    clone.removeAttribute("aria-hidden");
    Object.assign(clone.style, {
      position: "absolute",
      left: "0",
      top: "0",
      width: `${width}px`,
      height: `${height}px`,
      margin: "0",
      transform: "none",
      opacity: "1",
      visibility: "visible",
      pointerEvents: "none",
      overflow: "hidden",
      flex: "none",
      boxSizing: "border-box",
      zIndex: "1",
    });

    for (const element of clone.querySelectorAll("[data-anim], [data-delay]")) {
      Object.assign(element.style, {
        animation: "none",
        transition: "none",
        opacity: "1",
        transform: "none",
      });
    }

    root.appendChild(clone);
    document.body.appendChild(root);
    return { ok: true, selector: "#svglide-source-capture-root" };
  }, { index: activeIndex, width: args.width, height: args.height });
}

async function captureFamily(browser, family, args) {
  const familyId = family.family_id;
  const templatePath = path.join(SOURCE_ROOT, "templates", familyId, "template.html");
  const page = await browser.newPage({ viewport: { width: args.width, height: args.height }, deviceScaleFactor: 1 });
  await page.goto(pathToFileURL(templatePath).href, { waitUntil: "load" });
  await page.addStyleTag({
    content: `
      .nav-controls,
      .slide-counter,
      .keyboard-hint,
      .progress-bar {
        display: none !important;
      }
      #svglide-source-capture-root,
      #svglide-source-capture-root * {
        animation: none !important;
        transition: none !important;
      }
      #svglide-source-capture-root [data-anim] {
        opacity: 1 !important;
        transform: none !important;
      }
    `,
  });
  const slideCount = await page.evaluate(() => {
    const slideRoots = document.querySelectorAll(".slide");
    return slideRoots.length || document.querySelectorAll("section[data-screen-label]").length;
  });
  const records = [];
  for (const familyPage of family.pages || []) {
    const sourceSlideIndex = Number(familyPage.source_slide_index || familyPage.page);
    if (!Number.isInteger(sourceSlideIndex) || sourceSlideIndex < 1) {
      records.push({
        family_id: familyId,
        page_variant_id: familyPage.page_variant_id,
        source_slide_index: familyPage.source_slide_index,
        status: "missing_source_slide",
      });
      continue;
    }
    const activation = await setActiveSlide(page, Math.min(sourceSlideIndex - 1, slideCount - 1), familyPage.source_class);
    if (activation.activeIndex < 0 || activation.activeIndex >= activation.slideCount) {
      records.push({
        family_id: familyId,
        page_variant_id: familyPage.page_variant_id,
        source_slide_index: familyPage.source_slide_index,
        source_class: familyPage.source_class,
        status: "missing_source_slide",
      });
      continue;
    }
    const captureRoot = await createCaptureRoot(page, activation.activeIndex, args);
    if (!captureRoot.ok) {
      records.push({
        family_id: familyId,
        page_variant_id: familyPage.page_variant_id,
        source_slide_index: familyPage.source_slide_index,
        source_class: familyPage.source_class,
        status: "capture_root_failed",
        missing_reason: captureRoot.reason,
      });
      continue;
    }
    const outputPath = screenshotPath(args.outputDir, familyId, sourceSlideIndex, familyPage.page_variant_id);
    await mkdir(path.dirname(outputPath), { recursive: true });
    const locator = page.locator(captureRoot.selector);
    const buffer = await locator.screenshot({ type: "jpeg", quality: args.quality });
    await writeFile(outputPath, buffer);
    records.push({
      family_id: familyId,
      page_variant_id: familyPage.page_variant_id,
      page_role: familyPage.page_role,
      role_group: familyPage.role_group,
      source_slide_index: sourceSlideIndex,
      status: "generated",
      path: relpath(outputPath),
      sha256: sha256(buffer),
      bytes: buffer.length,
      width: args.width,
      height: args.height,
      source_template_html: `beautiful-html-templates/templates/${familyId}/template.html`,
    });
  }
  await page.close();
  return records;
}

async function main() {
  const args = parseArgs(process.argv);
  const manifest = await readJson(args.manifest);
  const families = (manifest.families || []).filter((family) => !args.family || family.family_id === args.family);
  const { chromium } = loadPlaywright(args.nodeModules);
  const browser = await chromium.launch({
    headless: true,
    executablePath: args.chrome,
  });
  const pages = [];
  try {
    for (const family of families) {
      pages.push(...(await captureFamily(browser, family, args)));
    }
  } finally {
    await browser.close();
  }
  const generated = pages.filter((page) => page.status === "generated");
  const receipt = {
    schema_version: "svglide-beautiful-source-page-screenshots/v1",
    artifact_kind: "beautiful_source_page_screenshot_receipt",
    generated_by: "beautiful_template_source_page_screenshot.mjs",
    source_manifest: relpath(path.resolve(args.manifest)),
    source_manifest_sha256: sha256(await readFile(args.manifest)),
    output_dir: relpath(path.resolve(args.outputDir)),
    not_promotion_receipt: true,
    summary: {
      family_count: families.length,
      page_count: pages.length,
      generated_count: generated.length,
      missing_count: pages.length - generated.length,
      total_bytes: generated.reduce((sum, item) => sum + Number(item.bytes || 0), 0),
    },
    pages,
  };
  await mkdir(path.dirname(args.receipt), { recursive: true });
  await writeFile(args.receipt, `${JSON.stringify(receipt, null, 2)}\n`);
  const output = {
    family_count: receipt.summary.family_count,
    page_count: receipt.summary.page_count,
    generated_count: receipt.summary.generated_count,
    missing_count: receipt.summary.missing_count,
    output_dir: path.resolve(args.outputDir),
    receipt_path: path.resolve(args.receipt),
  };
  console.log(JSON.stringify(output, null, args.pretty ? 2 : 0));
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : String(error));
  process.exit(1);
});
