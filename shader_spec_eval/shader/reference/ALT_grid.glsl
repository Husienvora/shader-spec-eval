void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    ivec2 c = ivec2(floor(fragCoord / iResolution.xy * vec2(6.0, 4.0)));
    bool odd = ((c.x + c.y) % 2) != 0;
    fragColor = vec4(odd ? vec3(1.0, 0.9, 0.03) : vec3(0.01), 1.0);
}
