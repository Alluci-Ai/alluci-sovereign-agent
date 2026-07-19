import re

with open(".venv/lib/python3.11/site-packages/mlx_lm/models/gemma4_text.py", "r") as f:
    text = f.read()

good = """        for idx, (layer, c, mask, prev_idx, per_layer_input) in enumerate(
            zip(
                self.layers,
                cache,
                masks,
                self.previous_kvs,
                per_layer_inputs,
            )
        ):
            kvs, offset = intermediates[prev_idx]

            h, kvs, offset = layer(
                h,
                mask,
                c,
                per_layer_input=per_layer_input,
                shared_kv=kvs,
                offset=offset,
            )

            intermediates[idx] = (kvs, offset)

        return self.norm(h)"""

bad_pattern = r"        for idx, \(layer, c, mask, prev_idx, per_layer_input\) in enumerate\([\s\S]*?return h_normediates\[idx\] = \(kvs, offset\)\n\n        return self\.norm\(h\)"
text = re.sub(bad_pattern, good, text)

with open(".venv/lib/python3.11/site-packages/mlx_lm/models/gemma4_text.py", "w") as f:
    f.write(text)

