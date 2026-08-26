# Eligibility amendment: DeepSeek compatibility pilot

The v0.3 run was paused after 20 DeepSeek cells. Only 4/20 responses
compiled (20%). The failures were returned by the model/provider route, not
introduced by the renderer: 11 responses omitted the required `mainImage`
wrapper, 5 redeclared predeclared uniforms, and multiple responses contained
malformed or non-GLSL tokens. All 20 requests were routed through GMICloud.

These cells remain in the raw checkpoint and are reported as a compatibility
pilot. DeepSeek is excluded from the primary v0.3 comparison, and no further
DeepSeek requests are made under this budget-constrained run. A provider-pinned
follow-up would be required before attributing this result to the model rather
than the route.
