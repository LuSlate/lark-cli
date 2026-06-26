// Copyright (c) 2026 Lark Technologies Pte. Ltd.
// SPDX-License-Identifier: MIT

package skillscheck

import (
	"encoding/json"
	"fmt"
	"regexp"
	"sort"
	"strings"
	"time"

	"github.com/larksuite/cli/internal/selfupdate"
)

var (
	skillNamePattern = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9_:-]*(@[^\s]+)?$`)
	ansiPattern      = regexp.MustCompile(`\x1b\[[0-?]*[ -/]*[@-~]`)
)

type SyncInput struct {
	Version        string
	OfficialSkills []string
	LocalSkills    []string
	PreviousState  *SkillsState
	StateReadable  bool
	Force          bool
}

// SuiteSelection 表示本次调用通过 --skills 传入的 suite 选择。
// All 为 true 表示 "--skills all"(重置为全部官方 skill);否则 Skills 为显式名单。
type SuiteSelection struct {
	All    bool
	Skills []string
}

// ParseSuiteSelection 解析 --skills 的原始值,只做格式校验(不校验名字是否是真实官方 skill)。
// 调用方仅在用户显式传入 --skills 时调用本函数。
func ParseSuiteSelection(rawNames []string) (*SuiteSelection, error) {
	seen := map[string]bool{}
	cleaned := []string{}
	hasAll := false
	for _, raw := range rawNames {
		name := strings.TrimSpace(raw)
		if name == "" {
			continue
		}
		if strings.EqualFold(name, "all") {
			hasAll = true
			continue
		}
		if seen[name] {
			continue
		}
		seen[name] = true
		cleaned = append(cleaned, name)
	}
	if hasAll {
		if len(cleaned) > 0 {
			return nil, fmt.Errorf("--skills all cannot be combined with other skill names")
		}
		return &SuiteSelection{All: true}, nil
	}
	if len(cleaned) == 0 {
		return nil, fmt.Errorf("--skills requires at least one skill name")
	}
	invalid := []string{}
	for _, name := range cleaned {
		if !skillNamePattern.MatchString(name) {
			invalid = append(invalid, name)
		}
	}
	if len(invalid) > 0 {
		return nil, fmt.Errorf("invalid skill name(s): %s (skill names use only letters, digits, and _ : -)", strings.Join(invalid, ", "))
	}
	sort.Strings(cleaned)
	return &SuiteSelection{Skills: cleaned}, nil
}

type SyncPlan struct {
	Version        string
	OfficialSkills []string
	ToUpdate       []string
	Added          []string
	SkippedDeleted []string
}

func stripANSI(s string) string {
	return ansiPattern.ReplaceAllString(s, "")
}

func ParseSkillsList(text string) []string {
	text = stripANSI(text)
	lines := strings.Split(text, "\n")

	// Detect format type
	hasGlobalSkills := strings.Contains(text, "Global Skills")
	hasAvailableSkills := strings.Contains(text, "Available Skills")

	if hasGlobalSkills {
		// Format 1: locally installed skills list from "npx -y skills ls -g"
		return parseGlobalSkillsList(lines)
	} else if hasAvailableSkills {
		// Format 2: official skills list from "npx -y skills add ... --list"
		return parseOfficialSkillsList(lines)
	}
	return nil
}

func ParseGlobalSkillsJSON(text string) []string {
	type globalSkill struct {
		Name string `json:"name"`
	}

	var skills []globalSkill
	if err := json.Unmarshal([]byte(text), &skills); err != nil {
		return nil
	}

	seen := map[string]bool{}
	for _, skill := range skills {
		candidate := strings.TrimSpace(skill.Name)
		if candidate == "" || !skillNamePattern.MatchString(candidate) {
			continue
		}
		seen[candidate] = true
	}

	return sortedKeys(seen)
}

func ParseOfficialSkillsIndexJSON(text string) ([]string, error) {
	type officialSkill struct {
		Name string `json:"name"`
	}
	type officialIndex struct {
		Skills []officialSkill `json:"skills"`
	}

	var index officialIndex
	if err := json.Unmarshal([]byte(text), &index); err != nil {
		return nil, err
	}

	seen := map[string]bool{}
	for _, skill := range index.Skills {
		candidate := strings.TrimSpace(skill.Name)
		if skillNamePattern.MatchString(candidate) {
			seen[candidate] = true
		}
	}

	return sortedKeys(seen), nil
}

// parseGlobalSkillsList parses the output of "npx -y skills ls -g"
func parseGlobalSkillsList(lines []string) []string {
	seen := map[string]bool{}

	for _, line := range lines {
		trimmed := strings.TrimSpace(line)

		// Skip header
		if strings.HasPrefix(trimmed, "Global Skills") {
			continue
		}

		// Skip empty lines
		if trimmed == "" {
			continue
		}
		if strings.HasPrefix(trimmed, "Tip:") {
			continue
		}

		if strings.HasPrefix(trimmed, "Agents:") {
			continue
		}

		if isGlobalSkillsSectionHeader(trimmed) {
			continue
		}

		// Extract skill name, format is typically "skill-name /path/to/skill"
		parts := strings.Fields(trimmed)
		if len(parts) == 0 {
			continue
		}

		candidate := parts[0]

		// Validate and add
		if candidate == "" || !skillNamePattern.MatchString(candidate) {
			continue
		}
		seen[candidate] = true
	}

	return sortedKeys(seen)
}

func isGlobalSkillsSectionHeader(line string) bool {
	switch line {
	case "General", "Project", "Local":
		return true
	default:
		return false
	}
}

// parseOfficialSkillsList parses the output of "npx -y skills add ... --list"
func parseOfficialSkillsList(lines []string) []string {
	seen := map[string]bool{}
	inAvailableSection := false

	for _, line := range lines {
		// Check if we've reached the "Available Skills" section
		if strings.Contains(line, "Available Skills") {
			inAvailableSection = true
			continue
		}

		if !inAvailableSection {
			continue
		}

		// Process lines containing "│", e.g. " │    lark-approval "
		if strings.Contains(line, "│") {
			// Remove all "│" characters and spaces, extract the first valid token in order
			parts := strings.FieldsFunc(line, func(r rune) bool {
				return r == '│' || r == ' '
			})

			if len(parts) > 0 {
				candidate := parts[0]
				if skillNamePattern.MatchString(candidate) {
					seen[candidate] = true
				}
			}
		}
	}

	return sortedKeys(seen)
}

func PlanSync(input SyncInput) SyncPlan {
	official := uniqueSorted(input.OfficialSkills)
	if input.Force {
		return SyncPlan{
			Version:        input.Version,
			OfficialSkills: official,
			ToUpdate:       official,
			Added:          []string{},
			SkippedDeleted: []string{},
		}
	}

	officialSet := toSet(official)
	installedOfficial := intersection(input.LocalSkills, officialSet)

	previousOfficial := []string{}
	if input.StateReadable && input.PreviousState != nil {
		previousOfficial = input.PreviousState.OfficialSkills
	}
	previousSet := toSet(previousOfficial)

	newAddedOfficial := []string{}
	for _, skill := range official {
		if !previousSet[skill] {
			newAddedOfficial = append(newAddedOfficial, skill)
		}
	}

	updateSet := toSet(installedOfficial)
	for _, skill := range newAddedOfficial {
		updateSet[skill] = true
	}
	toUpdate := sortedKeys(updateSet)
	updateSet = toSet(toUpdate)

	skipped := []string{}
	for _, skill := range official {
		if !updateSet[skill] {
			skipped = append(skipped, skill)
		}
	}

	return SyncPlan{
		Version:        input.Version,
		OfficialSkills: official,
		ToUpdate:       toUpdate,
		Added:          uniqueSorted(newAddedOfficial),
		SkippedDeleted: skipped,
	}
}

type SkillsRunner interface {
	ListOfficialSkillsIndex() *selfupdate.NpmResult
	ListOfficialSkills() *selfupdate.NpmResult
	ListGlobalSkillsJSON() *selfupdate.NpmResult
	ListGlobalSkills() *selfupdate.NpmResult
	InstallSkill(nameList []string) *selfupdate.NpmResult
	InstallAllSkills() *selfupdate.NpmResult
}

type SyncOptions struct {
	Version string
	Force   bool
	Runner  SkillsRunner
	Now     func() time.Time
	Suite   *SuiteSelection // nil = 本次未传 --skills(沿用 state 中的 sticky suite)
}

type SyncResult struct {
	Action         string
	Official       []string
	Updated        []string
	Added          []string
	SkippedDeleted []string
	Failed         []string
	Err            error
	Detail         string
	Force          bool
	Suite          []string // 生效的 suite(nil/空 = 全部模式)
	InvalidInput   bool     // true 表示因用户输入非法(未知 skill 名)而失败 → 命令层映射为 exit 2
}

// resolveEffectiveSuite 决定本次实际生效的 suite。
// 返回 (suite 名单, suiteActive)。suiteActive=false 表示全部模式。
func resolveEffectiveSuite(optSuite *SuiteSelection, previous *SkillsState, readable bool) ([]string, bool) {
	if optSuite != nil {
		if optSuite.All {
			return nil, false // 显式重置为全部
		}
		return optSuite.Skills, true
	}
	if readable && previous != nil && len(previous.SuiteSkills) > 0 {
		return previous.SuiteSkills, true // 沿用 sticky suite
	}
	return nil, false
}

// suiteSkillsForState 返回写入 state 的 SuiteSkills(全部模式时为 nil,使其被 omitempty 省略/清空)。
func suiteSkillsForState(active bool, suite []string) []string {
	if !active {
		return nil
	}
	return suite
}

func SyncSkills(opts SyncOptions) *SyncResult {
	if opts.Now == nil {
		opts.Now = time.Now
	}
	if opts.Runner == nil {
		return &SyncResult{Action: "failed", Err: fmt.Errorf("skills runner is nil")}
	}

	// 先读 previous state——解析 sticky suite 需要它,且即便后续官方列表失败也要能判断是否处于 suite 模式。
	previous, readable, err := ReadState()
	if err != nil {
		readable = false
		previous = nil
	}

	effectiveSuite, suiteActive := resolveEffectiveSuite(opts.Suite, previous, readable)

	// --- Step 1: List official skills ---
	official, reason, ok := listOfficialSkills(opts.Runner)
	if !ok {
		if suiteActive {
			// suite 模式绝不 fallback 装全部(会违背"只要子集"的意图)。
			return &SyncResult{
				Action: "failed",
				Err:    fmt.Errorf("cannot apply skills suite: official skills list unavailable (%s)", reason),
				Detail: reason,
				Force:  opts.Force,
				Suite:  effectiveSuite,
			}
		}
		return fallbackFullInstall(opts, reason, nil)
	}

	// --- Step 1.5: suite 模式下校验名字 + 收窄官方集合 ---
	if suiteActive {
		officialSet := toSet(official)
		unknown := []string{}
		for _, name := range effectiveSuite {
			if !officialSet[name] {
				unknown = append(unknown, name)
			}
		}
		if len(unknown) > 0 {
			return &SyncResult{
				Action:       "failed",
				InvalidInput: true,
				Err:          fmt.Errorf("unknown skill(s) not in official list: %s", strings.Join(unknown, ", ")),
				Force:        opts.Force,
				Suite:        effectiveSuite,
			}
		}
		official = intersection(official, toSet(effectiveSuite))
	}

	// --- Step 2: List local (installed) skills ---
	local, ok := listLocalSkills(opts.Runner)
	if !ok {
		if suiteActive {
			return &SyncResult{
				Action: "failed",
				Err:    fmt.Errorf("cannot apply skills suite: local skills list unavailable"),
				Force:  opts.Force,
				Suite:  effectiveSuite,
			}
		}
		return fallbackFullInstall(opts, "local skills list failed or parsed as empty", official)
	}

	// --- Step 3: Plan (previous state already read above) ---
	plan := PlanSync(SyncInput{
		Version:        opts.Version,
		OfficialSkills: official,
		LocalSkills:    local,
		PreviousState:  previous,
		StateReadable:  readable,
		Force:          opts.Force,
	})

	toInstall := plan.ToUpdate
	// suite 模式:若增量计算出"无需更新",仍要确保 suite 被安装(用户显式要这些 skill)。
	if suiteActive && len(toInstall) == 0 {
		toInstall = official
	}

	result := &SyncResult{
		Action:         "synced",
		Official:       plan.OfficialSkills,
		Updated:        toInstall,
		Added:          plan.Added,
		SkippedDeleted: plan.SkippedDeleted,
		Force:          opts.Force,
		Suite:          suiteSkillsForState(suiteActive, effectiveSuite),
	}

	if len(toInstall) == 0 {
		// 仅非 suite 模式才会到这里。
		return fallbackFullInstall(opts, "toUpdate skills empty fallback", official)
	}

	installResult := opts.Runner.InstallSkill(toInstall)
	if installResult == nil || installResult.Err != nil {
		if suiteActive {
			// suite 模式安装失败也不 fallback 装全部。
			return &SyncResult{
				Action: "failed",
				Err:    fmt.Errorf("skills suite install failed: %s", resultDetail(installResult)),
				Detail: resultDetail(installResult),
				Force:  opts.Force,
				Suite:  effectiveSuite,
			}
		}
		return fallbackFullInstall(opts, resultDetail(installResult), official)
	}

	state := SkillsState{
		Version:              opts.Version,
		OfficialSkills:       plan.OfficialSkills,
		UpdatedSkills:        toInstall,
		AddedOfficialSkills:  plan.Added,
		SkippedDeletedSkills: plan.SkippedDeleted,
		SuiteSkills:          suiteSkillsForState(suiteActive, effectiveSuite),
		UpdatedAt:            opts.Now().UTC().Format(time.RFC3339),
	}
	if err := WriteState(state); err != nil {
		result.Action = "failed"
		result.Err = fmt.Errorf("skills synced but state not written: %w", err)
		return result
	}

	return result
}

func listOfficialSkills(runner SkillsRunner) ([]string, string, bool) {
	reasons := []string{}

	indexResult := runner.ListOfficialSkillsIndex()
	if indexResult == nil || indexResult.Err != nil {
		reasons = append(reasons, "official skills index failed: "+resultDetail(indexResult))
	} else {
		official, err := ParseOfficialSkillsIndexJSON(indexResult.Stdout.String())
		if err != nil {
			reasons = append(reasons, "official skills index JSON invalid: "+err.Error())
		} else if len(official) > 0 {
			return official, "", true
		} else {
			reasons = append(reasons, "official skills index contains no skills")
		}
	}

	officialResult := runner.ListOfficialSkills()
	if officialResult == nil || officialResult.Err != nil {
		reasons = append(reasons, "official skills list failed: "+resultDetail(officialResult))
		return nil, strings.Join(reasons, "; "), false
	}
	official := ParseSkillsList(officialResult.Stdout.String())
	if len(official) > 0 {
		return official, "", true
	}
	if strings.TrimSpace(officialResult.Stdout.String()) != "" {
		reasons = append(reasons, "official skills list parsed as empty despite non-empty stdout")
	} else {
		reasons = append(reasons, "official skills list returned no skills")
	}
	return nil, strings.Join(reasons, "; "), false
}

func listLocalSkills(runner SkillsRunner) ([]string, bool) {
	jsonResult := runner.ListGlobalSkillsJSON()
	if jsonResult != nil && jsonResult.Err == nil {
		if local := ParseGlobalSkillsJSON(jsonResult.Stdout.String()); len(local) > 0 {
			return local, true
		}
	}

	textResult := runner.ListGlobalSkills()
	if textResult != nil && textResult.Err == nil {
		if local := ParseSkillsList(textResult.Stdout.String()); len(local) > 0 {
			return local, true
		}
	}

	return nil, false
}

// fallbackFullInstall performs a full skills install (npx -y skills add <source> -g -y)
// when incremental sync is not possible. On success it writes a state file so that
// subsequent syncs can use incremental mode. When official is non-nil the state
// records the full official list; otherwise a minimal state (version only) is
// written to break the fallback loop.
func fallbackFullInstall(opts SyncOptions, reason string, official []string) *SyncResult {
	installResult := opts.Runner.InstallAllSkills()
	if installResult == nil {
		return &SyncResult{
			Action: "fallback_failed",
			Err:    fmt.Errorf("full skills install failed: empty result (reason: %s)", reason),
			Detail: reason,
			Force:  opts.Force,
		}
	}
	if installResult.Err != nil {
		return &SyncResult{
			Action: "fallback_failed",
			Err:    fmt.Errorf("full skills install failed: %w (reason: %s)", installResult.Err, reason),
			Detail: reason + "\n" + resultDetail(installResult),
			Force:  opts.Force,
		}
	}

	state := SkillsState{
		Version:              opts.Version,
		OfficialSkills:       official,
		UpdatedSkills:        official,
		AddedOfficialSkills:  official,
		SkippedDeletedSkills: []string{},
		UpdatedAt:            opts.Now().UTC().Format(time.RFC3339),
	}
	if writeErr := WriteState(state); writeErr != nil {
		return &SyncResult{
			Action:         "fallback_synced",
			Official:       official,
			Updated:        official,
			Added:          official,
			SkippedDeleted: []string{},
			Detail:         reason + "\nstate write failed: " + writeErr.Error(),
			Force:          opts.Force,
		}
	}

	return &SyncResult{
		Action:         "fallback_synced",
		Official:       official,
		Updated:        official,
		Added:          official,
		SkippedDeleted: []string{},
		Detail:         reason,
		Force:          opts.Force,
	}
}

func resultDetail(result *selfupdate.NpmResult) string {
	if result == nil {
		return ""
	}
	parts := []string{}
	if output := strings.TrimSpace(result.CombinedOutput()); output != "" {
		parts = append(parts, output)
	}
	if result.Err != nil {
		parts = append(parts, result.Err.Error())
	}
	return strings.Join(parts, "\n")
}

func uniqueSorted(values []string) []string {
	return sortedKeys(toSet(values))
}

func toSet(values []string) map[string]bool {
	out := map[string]bool{}
	for _, value := range values {
		value = strings.TrimSpace(value)
		if value != "" {
			out[value] = true
		}
	}
	return out
}

// result = { x | x ∈ values ∧ x ∈ allowed }
func intersection(values []string, allowed map[string]bool) []string {
	out := map[string]bool{}
	for _, value := range values {
		if allowed[value] {
			out[value] = true
		}
	}
	return sortedKeys(out)
}

func sortedKeys(values map[string]bool) []string {
	out := make([]string, 0, len(values))
	for value := range values {
		out = append(out, value)
	}
	sort.Strings(out)
	return out
}
