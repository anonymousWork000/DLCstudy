import numpy as np
import scipy
from scipy import special
import tvm
import tvm.testing
import tvm.relay as relay
from tvm import topi
from tvm import te
from tvm.contrib import graph_runtime


def test_fastmath():
    def test_apply(relay_op, name, f_numpy, low, high, step, dtype="float32"):
        a_np = np.arange(low, high, step).astype(dtype)
        b_np = f_numpy(a_np)

        x = relay.var("x", shape=a_np.shape, dtype="float32")
        y = relay_op(x)
        func = relay.Function([x], y)
        mod = tvm.IRModule.from_expr(func)

        with tvm.transform.PassContext(opt_level=3, required_pass=["FastMath"]):
            graph, lib, params = relay.build(mod, target="llvm", params=None)

        # Check that the op related to fast math have been convered to function in lib
        func_name = "fused_" + name
        assert lib.get_function(func_name)

        ctx = tvm.cpu(0)
        m = graph_runtime.create(graph, lib, ctx)
        # Set inputs
        m.set_input("x", tvm.nd.array(a_np, ctx))
        m.set_input(**params)
        # Execute
        m.run()
        # Get outputs
        tvm_output = m.get_output(0)
        tvm.testing.assert_allclose(tvm_output.asnumpy(), b_np, rtol=1e-5, atol=1e-5)

    test_apply(relay.exp, "fast_exp", np.exp, low=-88, high=88, step=0.01)
    test_apply(relay.erf, "fast_erf", scipy.special.erf, low=-10, high=10, step=0.01)
    test_apply(relay.tanh, "fast_tanh", np.tanh, low=-10, high=10, step=0.01)
