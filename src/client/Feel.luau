-- Shared client-side state that the mount controller, camera, HUD and audio all read.
-- Plain table on purpose: scripts poll it every frame, and the few events use BindableEvents.
local Feel = {
	-- title screen -> gameplay
	started = false,
	introAlpha = 0, -- 0 = title camera, 1 = gameplay camera
	titleTime = 0,

	-- the local rider
	speed = 0, -- studs/second
	speedRatio = 0, -- 0..1 of gallop speed
	velocity = Vector3.zero,
	gait = "idle",
	sprinting = false,
	exhausted = false,
	stamina = 1, -- 0..1
	grounded = true,

	-- screen feel (decays by itself)
	shake = 0,
	fovKick = 0,

	-- mobile buttons
	touchSprint = false,

	Started = Instance.new("BindableEvent"),
	GaitChanged = Instance.new("BindableEvent"), -- (newGait)
	SprintBurst = Instance.new("BindableEvent"), -- fired when a gallop starts
	Emote = Instance.new("BindableEvent"), -- (name) "rear" | "toss"; fired by the on-screen buttons
}

function Feel.impulse(shake: number, fov: number?)
	Feel.shake = math.max(Feel.shake, shake)
	Feel.fovKick = math.max(Feel.fovKick, fov or 0)
end

function Feel.start()
	if Feel.started then
		return
	end
	Feel.started = true
	Feel.Started:Fire()
end

return Feel
