const fs = require('fs');
const parser = require('@babel/parser');

const filePath = process.argv[2]; 

try {
  const code = fs.readFileSync(filePath, 'utf-8');
  const parsed = parser.parse(code, {
    sourceType: "module",
    plugins: [
      "jsx",
      "typescript",
      "classProperties",
      "dynamicImport",
      "optionalChaining",
      "nullishCoalescingOperator",
      "objectRestSpread",
      "exportDefaultFrom",
      "exportNamespaceFrom",
      "exportExtensions",
      "functionBind",
      "functionSent",
      "doExpressions",
      "decorators-legacy",
      "classPrivateProperties",
      "classPrivateMethods",
      "privateIn",
      "logicalAssignment",
      "numericSeparator",
      "throwExpressions",
      "partialApplication",
      ["pipelineOperator", { "proposal": "minimal" }],
      "recordAndTuple"
    ]
  });

  const classes = [];
  const functions = [];
  const visitedNodes = new WeakSet(); 

  // Helper function to process nodes recursively
  function processNode(node) {
    if (!node || visitedNodes.has(node)) return;
    visitedNodes.add(node);

    // Handle specific node types
    if (node.type === 'ExportNamedDeclaration' || node.type === 'ExportDefaultDeclaration') {
      if (node.declaration) {
        processNode(node.declaration);
      }
    } else if (node.type === 'AssignmentExpression' && node.left.type === 'MemberExpression' && node.left.object.name === 'module' && node.left.property.name === 'exports') {
      // Handle module.exports = class Parser { ... }
      if (node.right.type === 'ClassDeclaration') {
        const className = node.right.id.name; // Get the class name directly
        classes.push({
          name: className,
          start_line: node.loc.start.line,
          end_line: node.loc.end.line,
          methods: [], // You can add method extraction logic here if needed
          isExported: true
        });
      } else if (node.right.type === 'ClassExpression') {
        // Handle anonymous class expressions
        const className = node.right.id ? node.right.id.name : '(anonymous)';
        classes.push({
          name: className,
          start_line: node.loc.start.line,
          end_line: node.loc.end.line,
          methods: [], // You can add method extraction logic here if needed
          isExported: true
        });
      }
    } else if (node.type === 'ClassDeclaration') {
      const methods = [];
      node.body.body.forEach(method => {
        if (method.type === 'ClassMethod') {
          methods.push({
            name: method.key.name,
            start_line: method.loc.start.line,
            end_line: method.loc.end.line
          });
        }
      });
      classes.push({
        name: node.id.name,
        start_line: node.loc.start.line,
        end_line: node.loc.end.line,
        methods: methods,
        isExported: false
      });
    } else if (node.type === 'FunctionDeclaration') {
      functions.push({
        name: node.id ? node.id.name : '(anonymous)',
        start_line: node.loc.start.line,
        end_line: node.loc.end.line
      });
    } else if (node.type === 'ExpressionStatement') {
      processNode(node.expression);
    } else if (node.type === 'VariableDeclaration') {
      node.declarations.forEach(declaration => {
        if (declaration.init) {
          if (declaration.init.type === 'ArrowFunctionExpression' || declaration.init.type === 'FunctionExpression') {
            functions.push({
              name: declaration.id.name,
              start_line: declaration.loc.start.line,
              end_line: declaration.loc.end.line
            });
          }
        }
      });
    }

    // General recursion: traverse all properties of the current node to find possible child nodes
    for (const key in node) {
      if (node.hasOwnProperty(key)) {
        const child = node[key];
        if (Array.isArray(child)) {
          child.forEach(c => {
            if (c && typeof c.type === 'string') {
              processNode(c);
            }
          });
        } else if (child && typeof child === 'object' && typeof child.type === 'string') {
          processNode(child);
        }
      }
    }
  }

  // Start processing the AST from the root node
  parsed.program.body.forEach(node => {
    processNode(node);
  });

  console.log(JSON.stringify({ classes, functions }));
} catch (error) {
  console.error(`Error parsing file ${filePath}: ${error.message}`);
  process.exit(1);
}
